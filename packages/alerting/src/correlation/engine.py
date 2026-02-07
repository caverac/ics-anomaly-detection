"""Correlation engine for grouping anomalies into incidents."""

from datetime import datetime, timedelta

import structlog

from src.config import CorrelationSettings
from src.kafka.consumer import AnomalyResult
from src.schemas.alert import Alert, AlertSeverity, AlertSource
from src.schemas.incident import Incident, IncidentPriority
from src.storage.redis_store import RedisStore

logger = structlog.get_logger()


class CorrelationEngine:
    """Groups anomalies into incidents based on correlation rules."""

    # Classification to severity mapping
    SEVERITY_MAP = {
        "normal": AlertSeverity.LOW,
        "suspicious": AlertSeverity.LOW,
        "anomaly": AlertSeverity.MEDIUM,
        "critical": AlertSeverity.CRITICAL,
    }

    def __init__(self, settings: CorrelationSettings, store: RedisStore) -> None:
        """Initialize the correlation engine."""
        self.settings = settings
        self.store = store
        self._incidents_created = 0
        self._incidents_updated = 0

    def process_anomaly(self, anomaly: AnomalyResult) -> tuple[Alert, Incident]:
        """Process an anomaly and return the generated alert and incident.

        Args:
            anomaly: The anomaly result to process.

        Returns:
            Tuple of (alert, incident).
        """
        # Generate correlation key
        correlation_key = Incident.generate_correlation_key(
            anomaly.window_key.src_ip,
            anomaly.window_key.dst_ip,
            anomaly.window_key.protocol,
        )

        # Find or create incident
        incident = self._get_or_create_incident(correlation_key, anomaly)

        # Create alert
        alert = self._create_alert(anomaly, incident)

        # Update incident with new anomaly
        incident.add_anomaly(
            alert_id=alert.id,
            ensemble_score=anomaly.ensemble_score,
            src_ip=anomaly.window_key.src_ip,
            dst_ip=anomaly.window_key.dst_ip,
            anomaly_type=anomaly.anomaly_type,
        )

        # Update incident title and description
        self._update_incident_description(incident)

        # Save both
        self.store.save_alert(alert)
        self.store.save_incident(incident)

        logger.info(
            "anomaly_correlated",
            alert_id=alert.id,
            incident_id=incident.id,
            anomaly_count=incident.anomaly_count,
            correlation_key=correlation_key,
        )

        return alert, incident

    def _get_or_create_incident(
        self, correlation_key: str, anomaly: AnomalyResult
    ) -> Incident:
        """Get existing incident or create a new one."""
        # Look for active incident within correlation window
        incident = self.store.get_incident_by_correlation_key(correlation_key)

        if incident:
            # Check if incident is within correlation window
            window_cutoff = datetime.utcnow() - timedelta(
                seconds=self.settings.window_seconds
            )
            if incident.updated_at >= window_cutoff:
                self._incidents_updated += 1
                return incident

        # Create new incident
        incident = Incident(
            correlation_key=correlation_key,
            priority=IncidentPriority.P4,
        )
        self._incidents_created += 1

        logger.info(
            "incident_created",
            incident_id=incident.id,
            correlation_key=correlation_key,
        )

        return incident

    def _create_alert(self, anomaly: AnomalyResult, incident: Incident) -> Alert:
        """Create an alert from an anomaly."""
        severity = self.SEVERITY_MAP.get(
            anomaly.classification.lower(), AlertSeverity.MEDIUM
        )

        # For high scores, bump up severity
        if anomaly.ensemble_score >= 0.9:
            severity = AlertSeverity.CRITICAL
        elif anomaly.ensemble_score >= 0.7 and severity == AlertSeverity.LOW:
            severity = AlertSeverity.MEDIUM

        title = self._generate_alert_title(anomaly)
        description = self._generate_alert_description(anomaly)

        return Alert(
            incident_id=incident.id,
            severity=severity,
            title=title,
            description=description,
            source=AlertSource(
                src_ip=anomaly.window_key.src_ip,
                dst_ip=anomaly.window_key.dst_ip,
                protocol=anomaly.window_key.protocol,
                window_size=anomaly.window_key.window_size,
                window_start=anomaly.window_key.window_start,
            ),
            anomaly_type=anomaly.anomaly_type,
            ensemble_score=anomaly.ensemble_score,
            confidence=anomaly.confidence,
            feature_contributions=anomaly.feature_contributions,
        )

    def _generate_alert_title(self, anomaly: AnomalyResult) -> str:
        """Generate a human-readable alert title."""
        anomaly_type = anomaly.anomaly_type or "Unknown"
        classification = anomaly.classification.capitalize()

        if anomaly_type.lower() == "unknown":
            return f"{classification} {anomaly.window_key.protocol.upper()} traffic from {anomaly.window_key.src_ip}"

        type_formatted = anomaly_type.replace("_", " ").title()
        return f"{type_formatted} detected from {anomaly.window_key.src_ip}"

    def _generate_alert_description(self, anomaly: AnomalyResult) -> str:
        """Generate a detailed alert description."""
        lines = [
            f"Anomaly detected in {anomaly.window_key.protocol.upper()} traffic",
            f"  Source: {anomaly.window_key.src_ip}",
            f"  Destination: {anomaly.window_key.dst_ip}",
            f"  Classification: {anomaly.classification}",
            f"  Ensemble Score: {anomaly.ensemble_score:.3f}",
            f"  Confidence: {anomaly.confidence:.3f}",
        ]

        if anomaly.anomaly_type:
            lines.append(f"  Type: {anomaly.anomaly_type}")

        if anomaly.feature_contributions:
            lines.append("  Top Features:")
            sorted_features = sorted(
                anomaly.feature_contributions.items(),
                key=lambda x: abs(x[1]),
                reverse=True,
            )[:5]
            for name, value in sorted_features:
                lines.append(f"    - {name}: {value:.3f}")

        return "\n".join(lines)

    def _update_incident_description(self, incident: Incident) -> None:
        """Update incident title and description."""
        if len(incident.anomaly_types) == 1:
            type_name = incident.anomaly_types[0].replace("_", " ").title()
            incident.title = f"{type_name} Incident"
        elif len(incident.anomaly_types) > 1:
            incident.title = f"Multi-type Anomaly Incident ({len(incident.anomaly_types)} types)"
        else:
            incident.title = "Anomaly Incident"

        incident.description = (
            f"Correlated incident with {incident.anomaly_count} anomalies. "
            f"Sources: {', '.join(incident.src_ips[:5])}. "
            f"Targets: {', '.join(incident.dst_ips[:5])}. "
            f"Max score: {incident.max_ensemble_score:.3f}"
        )

    def get_stats(self) -> dict[str, int]:
        """Get correlation statistics."""
        return {
            "incidents_created": self._incidents_created,
            "incidents_updated": self._incidents_updated,
        }
