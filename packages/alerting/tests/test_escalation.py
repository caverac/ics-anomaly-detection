"""Tests for escalation manager."""

import pytest

from src.config import EscalationSettings
from src.escalation.manager import EscalationManager
from src.schemas.alert import Alert, AlertSeverity, AlertSource
from src.schemas.incident import Incident, IncidentPriority


class TestEscalationManager:
    """Tests for EscalationManager."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return EscalationSettings(
            p3_threshold=5,
            p2_threshold=10,
            p1_threshold=20,
            multi_target_escalation=True,
            critical_severity_escalation=True,
        )

    @pytest.fixture
    def manager(self, settings):
        """Create escalation manager."""
        return EscalationManager(settings)

    def create_alert(self, severity: AlertSeverity = AlertSeverity.MEDIUM) -> Alert:
        """Create a test alert."""
        return Alert(
            severity=severity,
            title="Test Alert",
            description="Test",
            source=AlertSource(
                src_ip="10.0.0.1",
                dst_ip="10.0.0.2",
                protocol="modbus",
                window_size=60,
                window_start=0,
            ),
            ensemble_score=0.7,
            confidence=0.8,
        )

    def test_no_escalation_low_count(self, manager):
        """Test no escalation with low anomaly count."""
        incident = Incident(correlation_key="test:key:modbus")
        incident.anomaly_count = 2

        alert = self.create_alert()
        priority = manager.evaluate_escalation(incident, alert)

        assert priority == IncidentPriority.P4

    def test_escalation_to_p3(self, manager):
        """Test escalation to P3 threshold."""
        incident = Incident(correlation_key="test:key:modbus")
        incident.anomaly_count = 5

        alert = self.create_alert()
        priority = manager.evaluate_escalation(incident, alert)

        assert priority == IncidentPriority.P3

    def test_escalation_to_p2(self, manager):
        """Test escalation to P2 threshold."""
        incident = Incident(correlation_key="test:key:modbus")
        incident.anomaly_count = 10

        alert = self.create_alert()
        priority = manager.evaluate_escalation(incident, alert)

        assert priority == IncidentPriority.P2

    def test_escalation_to_p1(self, manager):
        """Test escalation to P1 threshold."""
        incident = Incident(correlation_key="test:key:modbus")
        incident.anomaly_count = 20

        alert = self.create_alert()
        priority = manager.evaluate_escalation(incident, alert)

        assert priority == IncidentPriority.P1

    def test_critical_severity_escalation(self, manager):
        """Test escalation on critical severity."""
        incident = Incident(correlation_key="test:key:modbus")
        incident.anomaly_count = 1

        alert = self.create_alert(AlertSeverity.CRITICAL)
        priority = manager.evaluate_escalation(incident, alert)

        assert priority == IncidentPriority.P2

    def test_multi_target_escalation(self, manager):
        """Test escalation on multi-target attack."""
        incident = Incident(correlation_key="test:key:modbus")
        incident.anomaly_count = 3
        incident.dst_ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]

        alert = self.create_alert()
        priority = manager.evaluate_escalation(incident, alert)

        assert priority == IncidentPriority.P2

    def test_disabled_multi_target_escalation(self, settings):
        """Test disabled multi-target escalation."""
        settings.multi_target_escalation = False
        manager = EscalationManager(settings)

        incident = Incident(correlation_key="test:key:modbus")
        incident.anomaly_count = 3
        incident.dst_ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]

        alert = self.create_alert()
        priority = manager.evaluate_escalation(incident, alert)

        assert priority == IncidentPriority.P4

    def test_stats_tracking(self, manager):
        """Test escalation stats are tracked."""
        incident = Incident(correlation_key="test:key:modbus")
        incident.anomaly_count = 5

        alert = self.create_alert()
        manager.evaluate_escalation(incident, alert)

        stats = manager.get_stats()
        assert stats["escalations"] == 1
