"""Escalation manager for incident priority management."""

import structlog

from src.config import EscalationSettings
from src.schemas.alert import Alert, AlertSeverity
from src.schemas.incident import Incident, IncidentPriority

logger = structlog.get_logger()


class EscalationManager:
    """Manages incident priority escalation."""

    def __init__(self, settings: EscalationSettings) -> None:
        """Initialize the escalation manager."""
        self.settings = settings
        self._escalations = 0

    def evaluate_escalation(self, incident: Incident, alert: Alert) -> IncidentPriority:
        """Evaluate if an incident should be escalated.

        Args:
            incident: The incident to evaluate.
            alert: The latest alert for this incident.

        Returns:
            The new priority for the incident.
        """
        current_priority = incident.priority
        new_priority = current_priority

        # Rule 1: Escalate based on anomaly count thresholds
        count_priority = self._evaluate_count_threshold(incident.anomaly_count)
        if self._is_higher_priority(count_priority, new_priority):
            new_priority = count_priority
            logger.info(
                "escalation_count_threshold",
                incident_id=incident.id,
                anomaly_count=incident.anomaly_count,
                new_priority=new_priority.value,
            )

        # Rule 2: Escalate on critical severity alerts
        if self.settings.critical_severity_escalation:
            if alert.severity == AlertSeverity.CRITICAL:
                severity_priority = IncidentPriority.P2
                if self._is_higher_priority(severity_priority, new_priority):
                    new_priority = severity_priority
                    logger.info(
                        "escalation_critical_severity",
                        incident_id=incident.id,
                        alert_id=alert.id,
                        new_priority=new_priority.value,
                    )

        # Rule 3: Escalate on multi-target attacks
        if self.settings.multi_target_escalation:
            if incident.is_multi_target() and len(incident.dst_ips) >= 3:
                multi_priority = IncidentPriority.P2
                if self._is_higher_priority(multi_priority, new_priority):
                    new_priority = multi_priority
                    logger.info(
                        "escalation_multi_target",
                        incident_id=incident.id,
                        target_count=len(incident.dst_ips),
                        new_priority=new_priority.value,
                    )

        # Track if we escalated
        if new_priority != current_priority:
            self._escalations += 1

        return new_priority

    def _evaluate_count_threshold(self, anomaly_count: int) -> IncidentPriority:
        """Determine priority based on anomaly count."""
        if anomaly_count >= self.settings.p1_threshold:
            return IncidentPriority.P1
        elif anomaly_count >= self.settings.p2_threshold:
            return IncidentPriority.P2
        elif anomaly_count >= self.settings.p3_threshold:
            return IncidentPriority.P3
        return IncidentPriority.P4

    def _is_higher_priority(
        self, candidate: IncidentPriority, current: IncidentPriority
    ) -> bool:
        """Check if candidate priority is higher than current.

        Note: P1 is highest priority, P4 is lowest.
        """
        priority_order = {
            IncidentPriority.P1: 0,
            IncidentPriority.P2: 1,
            IncidentPriority.P3: 2,
            IncidentPriority.P4: 3,
        }
        return priority_order[candidate] < priority_order[current]

    def get_stats(self) -> dict[str, int]:
        """Get escalation statistics."""
        return {
            "escalations": self._escalations,
        }
