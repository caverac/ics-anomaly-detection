"""Tests for anomaly detection models."""

import numpy as np
import pytest

from src.models.isolation_forest import IsolationForestModel
from src.models.one_class_svm import OneClassSVMModel
from src.models.ensemble import EnsembleModel


class TestIsolationForest:
    """Tests for Isolation Forest model."""

    def test_fit_and_predict(self) -> None:
        """Test model can fit and predict."""
        model = IsolationForestModel(n_estimators=10)

        X_train = np.random.randn(100, 10)
        model.fit(X_train)

        assert model.is_fitted

        X_test = np.random.randn(5, 10)
        scores = model.predict(X_test)

        assert scores.shape == (5,)
        assert np.all(scores >= 0)
        assert np.all(scores <= 1)

    def test_get_params(self) -> None:
        """Test parameter extraction."""
        model = IsolationForestModel(n_estimators=50, contamination=0.05)
        params = model.get_params()

        assert params["name"] == "isolation_forest"
        assert params["n_estimators"] == 50
        assert params["contamination"] == 0.05


class TestOneClassSVM:
    """Tests for One-Class SVM model."""

    def test_fit_and_predict(self) -> None:
        """Test model can fit and predict."""
        model = OneClassSVMModel(nu=0.1)

        X_train = np.random.randn(100, 10)
        model.fit(X_train)

        assert model.is_fitted

        X_test = np.random.randn(5, 10)
        scores = model.predict(X_test)

        assert scores.shape == (5,)
        assert np.all(scores >= 0)
        assert np.all(scores <= 1)


class TestEnsemble:
    """Tests for ensemble model."""

    def test_ensemble_predict(self) -> None:
        """Test ensemble combines model predictions."""
        isolation_forest = IsolationForestModel(n_estimators=10, weight=0.5)
        one_class_svm = OneClassSVMModel(nu=0.1, weight=0.5)

        X_train = np.random.randn(100, 10)
        isolation_forest.fit(X_train)
        one_class_svm.fit(X_train)

        ensemble = EnsembleModel(
            isolation_forest=isolation_forest,
            one_class_svm=one_class_svm,
        )

        X_test = np.random.randn(1, 10)
        score, model_scores, confidence = ensemble.predict(X_test)

        assert 0 <= score <= 1
        assert len(model_scores) == 2
        assert 0 <= confidence <= 1

    def test_ensemble_is_fitted(self) -> None:
        """Test ensemble reports fitted status."""
        ensemble = EnsembleModel()
        assert not ensemble.is_fitted

        isolation_forest = IsolationForestModel(n_estimators=10)
        isolation_forest.fit(np.random.randn(50, 5))

        ensemble.isolation_forest = isolation_forest
        assert ensemble.is_fitted
