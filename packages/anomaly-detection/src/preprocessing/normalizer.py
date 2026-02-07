"""Feature normalization for ML models."""

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import structlog
from sklearn.preprocessing import StandardScaler

logger = structlog.get_logger()


class FeatureNormalizer:
    """StandardScaler wrapper with persistence support.

    Normalizes features to zero mean and unit variance.
    Supports saving/loading for consistent normalization between
    training and inference.
    """

    def __init__(self) -> None:
        """Initialize the normalizer."""
        self._scaler = StandardScaler()
        self._is_fitted = False
        self._feature_names: list[str] = []

    @property
    def is_fitted(self) -> bool:
        """Check if normalizer has been fitted."""
        return self._is_fitted

    @property
    def feature_names(self) -> list[str]:
        """Get the list of feature names."""
        return self._feature_names

    @property
    def n_features(self) -> int:
        """Get the number of features."""
        return len(self._feature_names)

    def fit(self, X: np.ndarray, feature_names: list[str] | None = None) -> "FeatureNormalizer":
        """Fit the normalizer on training data.

        Args:
            X: Training data of shape (n_samples, n_features).
            feature_names: Optional list of feature names.

        Returns:
            The fitted normalizer.
        """
        self._scaler.fit(X)
        self._is_fitted = True

        if feature_names is not None:
            self._feature_names = feature_names
        else:
            self._feature_names = [f"feature_{i}" for i in range(X.shape[1])]

        logger.info(
            "normalizer_fitted",
            n_features=X.shape[1],
            n_samples=X.shape[0],
        )

        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Transform features using fitted scaler.

        Args:
            X: Input data of shape (n_samples, n_features).

        Returns:
            Normalized data of same shape.
        """
        if not self._is_fitted:
            raise RuntimeError("Normalizer not fitted. Call fit() first.")

        return self._scaler.transform(X)

    def fit_transform(
        self, X: np.ndarray, feature_names: list[str] | None = None
    ) -> np.ndarray:
        """Fit and transform in one step.

        Args:
            X: Training data of shape (n_samples, n_features).
            feature_names: Optional list of feature names.

        Returns:
            Normalized data of same shape.
        """
        self.fit(X, feature_names)
        return self.transform(X)

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        """Inverse transform to original scale.

        Args:
            X: Normalized data.

        Returns:
            Data in original scale.
        """
        if not self._is_fitted:
            raise RuntimeError("Normalizer not fitted. Call fit() first.")

        return self._scaler.inverse_transform(X)

    def save(self, path: Path) -> None:
        """Save the normalizer to disk.

        Args:
            path: Path to save the normalizer.
        """
        if not self._is_fitted:
            raise RuntimeError("Normalizer not fitted. Call fit() first.")

        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "scaler": self._scaler,
            "feature_names": self._feature_names,
        }
        joblib.dump(data, path)
        logger.info("normalizer_saved", path=str(path))

    def load(self, path: Path) -> None:
        """Load the normalizer from disk.

        Args:
            path: Path to load the normalizer from.
        """
        data = joblib.load(path)
        self._scaler = data["scaler"]
        self._feature_names = data["feature_names"]
        self._is_fitted = True
        logger.info("normalizer_loaded", path=str(path), n_features=len(self._feature_names))

    def get_stats(self) -> dict[str, Any]:
        """Get normalization statistics.

        Returns:
            Dictionary with mean and std for each feature.
        """
        if not self._is_fitted:
            return {}

        return {
            "mean": dict(zip(self._feature_names, self._scaler.mean_.tolist())),
            "std": dict(zip(self._feature_names, self._scaler.scale_.tolist())),
        }
