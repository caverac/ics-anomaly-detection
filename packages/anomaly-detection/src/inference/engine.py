"""Main inference engine for anomaly detection."""

from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import structlog

from src.config import ModelSettings, StorageSettings
from src.inference.classifier import AnomalyClassifier
from src.inference.hot_reload import ModelWatcher
from src.models.ensemble import EnsembleModel
from src.models.isolation_forest import IsolationForestModel
from src.models.lstm_autoencoder import LSTMAutoencoderModel
from src.models.one_class_svm import OneClassSVMModel
from src.preprocessing.normalizer import FeatureNormalizer
from src.preprocessing.sequence_builder import SequenceBuilder
from src.schemas.anomaly import AnomalyResult, WindowKey
from src.schemas.feature_vector import FeatureVector
from src.storage import ModelStore, create_model_store

logger = structlog.get_logger()


class InferenceEngine:
    """Main inference pipeline for anomaly detection.

    Orchestrates:
    - Feature normalization
    - Sequence building for LSTM
    - Ensemble model inference
    - Anomaly classification
    - Hot model reloading
    """

    def __init__(
        self,
        settings: ModelSettings,
        storage_settings: StorageSettings | None = None,
    ) -> None:
        """Initialize the inference engine.

        Args:
            settings: Model configuration settings.
            storage_settings: Storage configuration. If None, uses local storage
                with model_dir from settings.
        """
        self.settings = settings

        # Set up model storage
        if storage_settings is not None:
            self.store: ModelStore = create_model_store(storage_settings)
        else:
            # Backwards compatibility: use local storage with model_dir
            from src.storage.local import LocalModelStore

            self.store = LocalModelStore(model_dir=settings.model_dir)

        self.model_dir: Path = settings.model_dir  # May be updated after download

        self.ensemble = EnsembleModel(
            isolation_forest=IsolationForestModel(
                weight=settings.isolation_forest_weight,
            ),
            lstm_autoencoder=LSTMAutoencoderModel(
                weight=settings.lstm_autoencoder_weight,
                hidden_size=settings.lstm_hidden_size,
                num_layers=settings.lstm_num_layers,
            ),
            one_class_svm=OneClassSVMModel(
                weight=settings.one_class_svm_weight,
            ),
        )

        self.normalizer = FeatureNormalizer()
        self.sequence_builder = SequenceBuilder(
            sequence_length=settings.lstm_sequence_length,
            allow_padding=True,
        )

        self.classifier = AnomalyClassifier(
            suspicious_threshold=settings.suspicious_threshold,
            anomaly_threshold=settings.anomaly_threshold,
            critical_threshold=settings.critical_threshold,
        )

        self.watcher: ModelWatcher | None = None
        self._is_ready = False

    @property
    def is_ready(self) -> bool:
        """Check if engine is ready for inference."""
        return self._is_ready and self.ensemble.is_fitted

    def load_models(self) -> bool:
        """Load all models from storage.

        For S3 storage, downloads models to local cache first.
        For local storage, loads directly from disk.

        Returns:
            True if models loaded successfully.
        """
        try:
            # Download models if using remote storage
            logger.info(
                "loading_models",
                store_type=self.store.store_type,
            )
            self.model_dir = self.store.download_models()

            normalizer_path = self.model_dir / "normalizer.joblib"
            if normalizer_path.exists():
                self.normalizer.load(normalizer_path)
            else:
                logger.warning("normalizer_not_found", path=str(normalizer_path))
                return False

            self.ensemble.load_models(self.model_dir)

            if not self.ensemble.is_fitted:
                logger.warning("ensemble_not_fitted")
                return False

            self._is_ready = True
            logger.info(
                "inference_engine_ready",
                store_type=self.store.store_type,
                models_loaded=len(self.ensemble.models),
                n_features=self.normalizer.n_features,
            )
            return True

        except FileNotFoundError as e:
            logger.error("models_not_found", error=str(e))
            return False
        except ConnectionError as e:
            logger.error("storage_connection_failed", error=str(e))
            return False
        except Exception as e:
            logger.error("model_loading_failed", error=str(e))
            return False

    def start_hot_reload(self) -> None:
        """Start the model hot-reload watcher."""
        if not self.settings.hot_reload_enabled:
            return

        self.watcher = ModelWatcher(
            model_dir=self.model_dir,
            check_interval=float(self.settings.hot_reload_interval_seconds),
            on_reload=self._on_model_reload,
        )
        self.watcher.start(initial_ensemble=self.ensemble)

    def stop_hot_reload(self) -> None:
        """Stop the model hot-reload watcher."""
        if self.watcher is not None:
            self.watcher.stop()
            self.watcher = None

    def _on_model_reload(self, new_ensemble: EnsembleModel) -> None:
        """Handle model reload callback."""
        self.ensemble = new_ensemble
        logger.info("ensemble_updated_via_hot_reload")

    def predict(self, feature_vector: FeatureVector) -> AnomalyResult:
        """Run anomaly detection on a feature vector.

        Args:
            feature_vector: Input feature vector from feature-engine.

        Returns:
            AnomalyResult with ensemble score and classification.
        """
        if not self.is_ready:
            raise RuntimeError("Inference engine not ready. Call load_models() first.")

        features = feature_vector.to_ml_input()
        feature_array = self._features_to_array(features)

        X_normalized = self.normalizer.transform(feature_array)

        connection_key = feature_vector.get_connection_key()
        X_sequence = self.sequence_builder.add_vector(
            connection_key=connection_key,
            vector=X_normalized[0],
        )

        ensemble_score, model_scores, confidence = self.ensemble.predict(
            X_point=X_normalized,
            X_sequence=X_sequence,
        )

        classification = self.classifier.classify(ensemble_score)

        anomaly_type = self.classifier.identify_type(features, classification)

        stats = self.normalizer.get_stats()
        feature_contributions = {}
        if stats:
            feature_contributions = self.classifier.get_feature_contributions(
                features=features,
                means=stats.get("mean", {}),
                stds=stats.get("std", {}),
            )

        result = AnomalyResult(
            window_key=WindowKey(
                src_ip=feature_vector.window_key.src_ip,
                dst_ip=feature_vector.window_key.dst_ip,
                protocol=feature_vector.window_key.protocol,
                window_size=feature_vector.window_key.window_size,
                window_start=feature_vector.window_key.window_start,
            ),
            detected_at=datetime.utcnow(),
            model_scores=model_scores,
            ensemble_score=ensemble_score,
            classification=classification,
            anomaly_type=anomaly_type,
            confidence=confidence,
            feature_contributions=feature_contributions,
        )

        return result

    def _features_to_array(self, features: dict[str, float | int]) -> np.ndarray:
        """Convert feature dictionary to numpy array.

        Ensures consistent feature ordering based on normalizer's feature names.

        Args:
            features: Feature dictionary.

        Returns:
            Feature array of shape (1, n_features).
        """
        if not self.normalizer.is_fitted:
            values = [float(v) for v in sorted(features.values())]
            return np.array([values])

        values = []
        for name in self.normalizer.feature_names:
            if name in features:
                values.append(float(features[name]))
            else:
                values.append(0.0)

        return np.array([values])

    def get_stats(self) -> dict[str, Any]:
        """Get engine statistics.

        Returns:
            Dictionary with engine stats.
        """
        return {
            "is_ready": self.is_ready,
            "models": {m.name: m.is_fitted for m in self.ensemble.models},
            "sequence_builder": self.sequence_builder.get_stats(),
            "thresholds": self.classifier.get_thresholds(),
            "hot_reload_enabled": self.settings.hot_reload_enabled,
        }

    def close(self) -> None:
        """Clean up resources."""
        self.stop_hot_reload()
        self.ensemble.close()
        logger.info("inference_engine_closed")
