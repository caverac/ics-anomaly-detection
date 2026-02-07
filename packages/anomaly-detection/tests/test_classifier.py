"""Tests for anomaly classifier."""

import pytest

from src.inference.classifier import AnomalyClassifier
from src.schemas.anomaly import AnomalyType, Classification


class TestAnomalyClassifier:
    """Tests for anomaly classifier."""

    def test_classification_thresholds(self) -> None:
        """Test classification at different thresholds."""
        classifier = AnomalyClassifier(
            suspicious_threshold=0.4,
            anomaly_threshold=0.7,
            critical_threshold=0.9,
        )

        assert classifier.classify(0.1) == Classification.NORMAL
        assert classifier.classify(0.5) == Classification.SUSPICIOUS
        assert classifier.classify(0.75) == Classification.ANOMALY
        assert classifier.classify(0.95) == Classification.CRITICAL

    def test_boundary_values(self) -> None:
        """Test classification at exact boundaries."""
        classifier = AnomalyClassifier(
            suspicious_threshold=0.4,
            anomaly_threshold=0.7,
            critical_threshold=0.9,
        )

        assert classifier.classify(0.4) == Classification.SUSPICIOUS
        assert classifier.classify(0.7) == Classification.ANOMALY
        assert classifier.classify(0.9) == Classification.CRITICAL

    def test_identify_type_normal(self) -> None:
        """Test type identification for normal traffic."""
        classifier = AnomalyClassifier()

        anomaly_type = classifier.identify_type(
            features={"message_count": 10, "bytes_total": 1000},
            classification=Classification.NORMAL,
        )

        assert anomaly_type is None

    def test_identify_timing_anomaly(self) -> None:
        """Test timing anomaly identification."""
        classifier = AnomalyClassifier()

        features = {
            "iat_mean": 0.01,
            "iat_std": 0.5,
            "iat_min": 0.0001,
            "iat_max": 2.0,
            "message_count": 50,
            "bytes_mean": 100,
        }

        anomaly_type = classifier.identify_type(
            features=features,
            classification=Classification.ANOMALY,
        )

        assert anomaly_type == AnomalyType.TIMING_ANOMALY

    def test_identify_volume_anomaly(self) -> None:
        """Test volume anomaly identification."""
        classifier = AnomalyClassifier()

        features = {
            "message_count": 5000,
            "bytes_total": 2000000,
            "bytes_std": 1000,
            "iat_mean": 0.1,
            "iat_std": 0.01,
            "bytes_mean": 400,
        }

        anomaly_type = classifier.identify_type(
            features=features,
            classification=Classification.ANOMALY,
        )

        assert anomaly_type == AnomalyType.VOLUME_ANOMALY

    def test_feature_contributions(self) -> None:
        """Test feature contribution calculation."""
        classifier = AnomalyClassifier()

        # a deviates by 2 std, b deviates by 1 std
        features = {"a": 7.0, "b": 60.0}
        means = {"a": 5.0, "b": 50.0}
        stds = {"a": 1.0, "b": 10.0}

        contributions = classifier.get_feature_contributions(features, means, stds)

        assert "a" in contributions
        assert "b" in contributions
        assert contributions["a"] > contributions["b"]

    def test_get_thresholds(self) -> None:
        """Test threshold extraction."""
        classifier = AnomalyClassifier(
            suspicious_threshold=0.3,
            anomaly_threshold=0.6,
            critical_threshold=0.85,
        )

        thresholds = classifier.get_thresholds()

        assert thresholds["suspicious"] == 0.3
        assert thresholds["anomaly"] == 0.6
        assert thresholds["critical"] == 0.85
