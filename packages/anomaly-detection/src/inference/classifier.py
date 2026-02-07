"""Threshold-based anomaly classification."""

from typing import Any

import numpy as np
import structlog

from src.schemas.anomaly import AnomalyType, Classification

logger = structlog.get_logger()


class AnomalyClassifier:
    """Classifies ensemble scores into anomaly categories.

    Uses configurable thresholds to map continuous scores to
    discrete classifications. Also attempts to identify anomaly type
    based on feature contributions.
    """

    def __init__(
        self,
        suspicious_threshold: float = 0.4,
        anomaly_threshold: float = 0.7,
        critical_threshold: float = 0.9,
    ) -> None:
        """Initialize the classifier.

        Args:
            suspicious_threshold: Score above which is suspicious.
            anomaly_threshold: Score above which is an anomaly.
            critical_threshold: Score above which is critical.
        """
        self.suspicious_threshold = suspicious_threshold
        self.anomaly_threshold = anomaly_threshold
        self.critical_threshold = critical_threshold

    def classify(self, score: float) -> Classification:
        """Classify an ensemble score.

        Args:
            score: Ensemble anomaly score in [0, 1].

        Returns:
            Classification level.
        """
        if score >= self.critical_threshold:
            return Classification.CRITICAL
        elif score >= self.anomaly_threshold:
            return Classification.ANOMALY
        elif score >= self.suspicious_threshold:
            return Classification.SUSPICIOUS
        else:
            return Classification.NORMAL

    def identify_type(
        self,
        features: dict[str, float | int],
        classification: Classification,
    ) -> AnomalyType | None:
        """Attempt to identify the type of anomaly.

        Uses heuristics based on which features deviate most from normal.

        Args:
            features: Feature dictionary from the input vector.
            classification: The classification level.

        Returns:
            Identified anomaly type or None if normal.
        """
        if classification == Classification.NORMAL:
            return None

        timing_score = self._score_timing_anomaly(features)
        volume_score = self._score_volume_anomaly(features)
        recon_score = self._score_reconnaissance(features)

        scores = {
            AnomalyType.TIMING_ANOMALY: timing_score,
            AnomalyType.VOLUME_ANOMALY: volume_score,
            AnomalyType.RECONNAISSANCE: recon_score,
        }

        if max(scores.values()) < 0.3:
            return AnomalyType.UNKNOWN

        return max(scores, key=lambda k: scores[k])

    def _score_timing_anomaly(self, features: dict[str, float | int]) -> float:
        """Score likelihood of timing-based anomaly.

        Timing anomalies show unusual inter-arrival time patterns.
        """
        iat_std = features.get("iat_std", 0.0)
        iat_mean = features.get("iat_mean", 1.0)
        iat_max = features.get("iat_max", 0.0)
        iat_min = features.get("iat_min", 0.0)

        if iat_mean < 1e-10:
            return 0.0

        cv = float(iat_std) / max(float(iat_mean), 1e-10)

        iat_range = float(iat_max) - float(iat_min)
        range_ratio = iat_range / max(float(iat_mean), 1e-10)

        score = min(1.0, (cv * 0.5 + min(range_ratio, 10.0) / 10.0 * 0.5))
        return score

    def _score_volume_anomaly(self, features: dict[str, float | int]) -> float:
        """Score likelihood of volume-based anomaly.

        Volume anomalies show unusual message counts or byte sizes.
        """
        message_count = features.get("message_count", 0)
        bytes_total = features.get("bytes_total", 0)
        bytes_std = features.get("bytes_std", 0.0)

        score = 0.0

        if message_count > 1000:
            score += 0.4
        elif message_count < 5:
            score += 0.2

        if bytes_total > 1000000:
            score += 0.3

        if float(bytes_std) > 500:
            score += 0.3

        return min(1.0, score)

    def _score_reconnaissance(self, features: dict[str, float | int]) -> float:
        """Score likelihood of reconnaissance activity.

        Reconnaissance often shows many small messages with regular timing.
        """
        message_count = features.get("message_count", 0)
        bytes_mean = features.get("bytes_mean", 0.0)
        iat_std = features.get("iat_std", 0.0)
        iat_mean = features.get("iat_mean", 1.0)

        score = 0.0

        if message_count > 100 and float(bytes_mean) < 50:
            score += 0.5

        if iat_mean > 0 and float(iat_std) / max(float(iat_mean), 1e-10) < 0.1:
            score += 0.3

        if message_count > 500:
            score += 0.2

        return min(1.0, score)

    def get_feature_contributions(
        self,
        features: dict[str, float | int],
        means: dict[str, float],
        stds: dict[str, float],
    ) -> dict[str, float]:
        """Calculate how much each feature contributes to anomaly score.

        Uses z-scores to measure deviation from normal.

        Args:
            features: Current feature values.
            means: Mean values from training.
            stds: Standard deviations from training.

        Returns:
            Dictionary of feature name to contribution score.
        """
        contributions: dict[str, float] = {}

        for name, value in features.items():
            if name in means and name in stds:
                mean = means[name]
                std = stds.get(name, 1.0)
                if std < 1e-10:
                    std = 1.0

                z_score = abs(float(value) - mean) / std
                normalized = min(1.0, z_score / 3.0)
                contributions[name] = normalized

        return contributions

    def get_thresholds(self) -> dict[str, float]:
        """Get current threshold values."""
        return {
            "suspicious": self.suspicious_threshold,
            "anomaly": self.anomaly_threshold,
            "critical": self.critical_threshold,
        }
