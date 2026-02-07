"""Console notification channel for logging alerts."""

import structlog

from src.notifications.base import NotificationChannel
from src.schemas.alert import Alert, AlertSeverity
from src.schemas.incident import Incident, IncidentPriority

logger = structlog.get_logger()


class ConsoleNotifier(NotificationChannel):
    """Console/log notification channel."""

    def __init__(self, enabled: bool = True) -> None:
        """Initialize the console notifier."""
        self._enabled = enabled

    @property
    def name(self) -> str:
        """Return the channel name."""
        return "console"

    @property
    def enabled(self) -> bool:
        """Return whether the channel is enabled."""
        return self._enabled

    async def send_alert(self, alert: Alert, incident: Incident) -> bool:
        """Log alert to console/structured logs."""
        severity_indicator = self._get_severity_indicator(alert.severity)

        logger.info(
            f"{severity_indicator} ALERT",
            alert_id=alert.id,
            incident_id=incident.id,
            severity=alert.severity.value,
            title=alert.title,
            src_ip=alert.source.src_ip,
            dst_ip=alert.source.dst_ip,
            protocol=alert.source.protocol,
            score=f"{alert.ensemble_score:.3f}",
            anomaly_type=alert.anomaly_type,
            incident_anomaly_count=incident.anomaly_count,
            incident_priority=incident.priority.value,
        )

        return True

    async def send_escalation(self, incident: Incident, old_priority: str) -> bool:
        """Log escalation to console/structured logs."""
        priority_indicator = self._get_priority_indicator(incident.priority)

        logger.warning(
            f"{priority_indicator} ESCALATION",
            incident_id=incident.id,
            old_priority=old_priority,
            new_priority=incident.priority.value,
            anomaly_count=incident.anomaly_count,
            title=incident.title,
            src_ips=incident.src_ips[:5],
            dst_ips=incident.dst_ips[:5],
        )

        return True

    def _get_severity_indicator(self, severity: AlertSeverity) -> str:
        """Get a text indicator for severity level."""
        indicators = {
            AlertSeverity.LOW: "[LOW]",
            AlertSeverity.MEDIUM: "[MEDIUM]",
            AlertSeverity.HIGH: "[HIGH]",
            AlertSeverity.CRITICAL: "[CRITICAL]",
        }
        return indicators.get(severity, "[?]")

    def _get_priority_indicator(self, priority: IncidentPriority) -> str:
        """Get a text indicator for priority level."""
        indicators = {
            IncidentPriority.P4: "[P4]",
            IncidentPriority.P3: "[P3]",
            IncidentPriority.P2: "[P2]",
            IncidentPriority.P1: "[P1]",
        }
        return indicators.get(priority, "[?]")
