"""Training pipeline for anomaly detection models."""

from datetime import datetime
from pathlib import Path

import numpy as np
import structlog

from src.config import KafkaSettings, TrainingSettings
from src.models.ensemble import EnsembleModel
from src.models.isolation_forest import IsolationForestModel
from src.models.lstm_autoencoder import LSTMAutoencoderModel
from src.models.one_class_svm import OneClassSVMModel
from src.preprocessing.normalizer import FeatureNormalizer
from src.training.data_loader import TrainingDataLoader
from src.training.mlflow_tracker import MLflowTracker

logger = structlog.get_logger()


class TrainingPipeline:
    """Orchestrates training of all anomaly detection models.

    Handles:
    - Data loading and preprocessing
    - Training of each model type
    - Model saving
    - MLflow tracking
    """

    def __init__(self, settings: TrainingSettings) -> None:
        """Initialize the training pipeline.

        Args:
            settings: Training configuration.
        """
        self.settings = settings
        self.data_loader = TrainingDataLoader(settings)
        self.tracker = MLflowTracker(
            tracking_uri=settings.mlflow_tracking_uri,
            experiment_name=settings.mlflow_experiment_name,
        )
        self.normalizer = FeatureNormalizer()

    def train(
        self,
        kafka_settings: KafkaSettings | None = None,
        data_path: Path | None = None,
        max_samples: int = 10000,
    ) -> EnsembleModel:
        """Run the full training pipeline.

        Args:
            kafka_settings: Kafka settings for loading from topic.
            data_path: Path to training data file.
            max_samples: Maximum samples to load from Kafka.

        Returns:
            Trained ensemble model.
        """
        run_name = f"training-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.tracker.start_run(
            run_name=run_name,
            tags={"pipeline": "anomaly-detection"},
        )

        try:
            logger.info("training_pipeline_started")

            features, feature_names = self._load_data(
                kafka_settings=kafka_settings,
                data_path=data_path,
                max_samples=max_samples,
            )

            self.tracker.log_params(
                {
                    "n_samples": features.shape[0],
                    "n_features": features.shape[1],
                }
            )

            X_train, X_val = self._prepare_data(features, feature_names)

            ensemble = self._train_models(X_train, features)

            metrics = self._evaluate_models(ensemble, X_val, features)
            self.tracker.log_metrics(metrics)

            self._save_models(ensemble)

            logger.info(
                "training_pipeline_complete",
                n_samples=features.shape[0],
                output_dir=str(self.settings.output_dir),
            )

            return ensemble

        except Exception as e:
            logger.error("training_pipeline_failed", error=str(e))
            self.tracker.end_run(status="FAILED")
            raise

        finally:
            self.tracker.end_run()

    def _load_data(
        self,
        kafka_settings: KafkaSettings | None,
        data_path: Path | None,
        max_samples: int,
    ) -> tuple[np.ndarray, list[str]]:
        """Load training data from source.

        Args:
            kafka_settings: Kafka settings for loading from topic.
            data_path: Path to training data file.
            max_samples: Maximum samples to load.

        Returns:
            Tuple of (features, feature_names).
        """
        if data_path is not None:
            logger.info("loading_from_file", path=str(data_path))
            return self.data_loader.load_from_file(data_path)

        if kafka_settings is not None:
            logger.info("loading_from_kafka")
            vectors, feature_names = self.data_loader.load_from_kafka(
                kafka_settings=kafka_settings,
                max_messages=max_samples,
            )
            return self.data_loader.vectors_to_array(vectors)

        logger.info("loading_from_directory", path=str(self.settings.data_dir))
        return self.data_loader.load_from_directory()

    def _prepare_data(
        self, features: np.ndarray, feature_names: list[str]
    ) -> tuple[np.ndarray, np.ndarray]:
        """Prepare data for training.

        Args:
            features: Raw feature array.
            feature_names: List of feature names.

        Returns:
            Tuple of (X_train, X_val) normalized arrays.
        """
        n_samples = features.shape[0]
        n_val = int(n_samples * self.settings.validation_split)
        n_train = n_samples - n_val

        indices = np.random.permutation(n_samples)
        train_idx = indices[:n_train]
        val_idx = indices[n_train:]

        X_train_raw = features[train_idx]
        X_val_raw = features[val_idx]

        X_train = self.normalizer.fit_transform(X_train_raw, feature_names)
        X_val = self.normalizer.transform(X_val_raw)

        logger.info(
            "data_prepared",
            train_samples=X_train.shape[0],
            val_samples=X_val.shape[0],
        )

        return X_train, X_val

    def _train_models(
        self, X_train: np.ndarray, X_raw: np.ndarray
    ) -> EnsembleModel:
        """Train all models in the ensemble.

        Args:
            X_train: Normalized training data for point models.
            X_raw: Raw data for sequence building.

        Returns:
            Trained ensemble model.
        """
        isolation_forest = IsolationForestModel(
            n_estimators=self.settings.isolation_forest_n_estimators,
            contamination=self.settings.isolation_forest_contamination,
        )
        logger.info("training_isolation_forest")
        isolation_forest.fit(X_train)
        self.tracker.log_model_summary("isolation_forest", isolation_forest.get_params())

        one_class_svm = OneClassSVMModel(
            nu=self.settings.svm_nu,
            kernel=self.settings.svm_kernel,
            gamma=self.settings.svm_gamma,
        )
        logger.info("training_one_class_svm")
        one_class_svm.fit(X_train)
        self.tracker.log_model_summary("one_class_svm", one_class_svm.get_params())

        X_sequences = self.data_loader.build_sequences(
            X_train,
            sequence_length=10,
            stride=1,
        )

        lstm_autoencoder = LSTMAutoencoderModel(
            hidden_size=64,
            num_layers=2,
            epochs=self.settings.epochs,
            batch_size=self.settings.batch_size,
            learning_rate=self.settings.learning_rate,
        )
        logger.info("training_lstm_autoencoder")
        lstm_autoencoder.fit(X_sequences)
        self.tracker.log_model_summary("lstm_autoencoder", lstm_autoencoder.get_params())

        ensemble = EnsembleModel(
            isolation_forest=isolation_forest,
            lstm_autoencoder=lstm_autoencoder,
            one_class_svm=one_class_svm,
        )

        return ensemble

    def _evaluate_models(
        self, ensemble: EnsembleModel, X_val: np.ndarray, X_raw: np.ndarray
    ) -> dict[str, float]:
        """Evaluate models on validation data.

        Args:
            ensemble: Trained ensemble.
            X_val: Validation data.
            X_raw: Raw data for sequence building.

        Returns:
            Dictionary of evaluation metrics.
        """
        metrics: dict[str, float] = {}

        if ensemble.isolation_forest is not None:
            if_scores = ensemble.isolation_forest.predict(X_val)
            metrics["isolation_forest_mean_score"] = float(np.mean(if_scores))
            metrics["isolation_forest_std_score"] = float(np.std(if_scores))

        if ensemble.one_class_svm is not None:
            svm_scores = ensemble.one_class_svm.predict(X_val)
            metrics["one_class_svm_mean_score"] = float(np.mean(svm_scores))
            metrics["one_class_svm_std_score"] = float(np.std(svm_scores))

        if ensemble.lstm_autoencoder is not None:
            X_val_seq = self.data_loader.build_sequences(X_val, sequence_length=10)
            lstm_scores = ensemble.lstm_autoencoder.predict(X_val_seq)
            metrics["lstm_autoencoder_mean_score"] = float(np.mean(lstm_scores))
            metrics["lstm_autoencoder_std_score"] = float(np.std(lstm_scores))

        logger.info("evaluation_complete", metrics=metrics)
        return metrics

    def _save_models(self, ensemble: EnsembleModel) -> None:
        """Save all models and normalizer to disk.

        Args:
            ensemble: Trained ensemble to save.
        """
        output_dir = self.settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        self.normalizer.save(output_dir / "normalizer.joblib")
        self.tracker.log_artifact(output_dir / "normalizer.joblib")

        ensemble.save_models(output_dir)

        for model_file in output_dir.glob("*"):
            if model_file.is_file():
                self.tracker.log_artifact(model_file)

        logger.info("models_saved", output_dir=str(output_dir))
