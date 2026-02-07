"""Tests for alert and incident schemas."""

import pytest
from datetime import datetime

from src.schemas.alert import Alert, AlertSeverity, AlertSource, AlertStatus
from src.schemas.incident import Incident, IncidentPriority, IncidentStatus


class TestAlert:
    """Tests for Alert schema."""

    def test_alert_creation(self):
        """Test creating an alert with all required fields."""
        alert = Alert(
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            description="Test description",
            source=AlertSource(
                src_ip="192.168.1.100",
                dst_ip="192.168.1.1",
                protocol="modbus",
                window_size=60,
                window_start=1000,
            ),
            ensemble_score=0.85,
            confidence=0.9,
        )

        assert alert.id is not None
        assert alert.severity == AlertSeverity.HIGH
        assert alert.status == AlertStatus.OPEN
        assert alert.source.src_ip == "192.168.1.100"
        assert alert.ensemble_score == 0.85

    def test_alert_get_message_key(self):
        """Test message key generation."""
        alert = Alert(
            severity=AlertSeverity.MEDIUM,
            title="Test",
            description="Test",
            source=AlertSource(
                src_ip="10.0.0.1",
                dst_ip="10.0.0.2",
                protocol="dnp3",
                window_size=60,
                window_start=0,
            ),
            ensemble_score=0.5,
            confidence=0.7,
        )

        key = alert.get_message_key()
        assert key == "10.0.0.1:10.0.0.2:dnp3"

    def test_alert_get_dedup_key(self):
        """Test deduplication key generation."""
        alert = Alert(
            severity=AlertSeverity.LOW,
            title="Test",
            description="Test",
            source=AlertSource(
                src_ip="10.0.0.1",
                dst_ip="10.0.0.2",
                protocol="modbus",
                window_size=60,
                window_start=0,
            ),
            anomaly_type="reconnaissance",
            ensemble_score=0.3,
            confidence=0.5,
        )

        key = alert.get_dedup_key()
        assert key == "10.0.0.1:10.0.0.2:modbus:reconnaissance"

    def test_alert_to_kafka_message(self):
        """Test Kafka message conversion."""
        alert = Alert(
            severity=AlertSeverity.CRITICAL,
            title="Critical Alert",
            description="Critical test",
            source=AlertSource(
                src_ip="1.2.3.4",
                dst_ip="5.6.7.8",
                protocol="opcua",
                window_size=300,
                window_start=5000,
            ),
            ensemble_score=0.95,
            confidence=0.99,
        )

        msg = alert.to_kafka_message()
        assert isinstance(msg, dict)
        assert msg["severity"] == "critical"
        assert msg["title"] == "Critical Alert"
        assert msg["source"]["src_ip"] == "1.2.3.4"


class TestIncident:
    """Tests for Incident schema."""

    def test_incident_creation(self):
        """Test creating an incident."""
        incident = Incident(
            correlation_key="192.168.1.1:192.168.1.2:modbus",
        )

        assert incident.id is not None
        assert incident.status == IncidentStatus.ACTIVE
        assert incident.priority == IncidentPriority.P4
        assert incident.anomaly_count == 0

    def test_incident_add_anomaly(self):
        """Test adding anomalies to an incident."""
        incident = Incident(
            correlation_key="test:key:modbus",
        )

        incident.add_anomaly(
            alert_id="alert-1",
            ensemble_score=0.6,
            src_ip="10.0.0.1",
            dst_ip="10.0.0.2",
            anomaly_type="reconnaissance",
        )

        assert incident.anomaly_count == 1
        assert "alert-1" in incident.alert_ids
        assert incident.max_ensemble_score == 0.6
        assert "10.0.0.1" in incident.src_ips
        assert "reconnaissance" in incident.anomaly_types

        incident.add_anomaly(
            alert_id="alert-2",
            ensemble_score=0.8,
            src_ip="10.0.0.1",
            dst_ip="10.0.0.3",
            anomaly_type="volume_anomaly",
        )

        assert incident.anomaly_count == 2
        assert incident.max_ensemble_score == 0.8
        assert len(incident.dst_ips) == 2
        assert len(incident.anomaly_types) == 2

    def test_incident_multi_target(self):
        """Test multi-target detection."""
        incident = Incident(correlation_key="test:key:modbus")

        incident.add_anomaly("a1", 0.5, "10.0.0.1", "10.0.0.2", None)
        assert not incident.is_multi_target()

        incident.add_anomaly("a2", 0.5, "10.0.0.1", "10.0.0.3", None)
        assert incident.is_multi_target()

    def test_generate_correlation_key(self):
        """Test correlation key generation."""
        key = Incident.generate_correlation_key("10.0.0.1", "10.0.0.2", "modbus")
        assert key == "10.0.0.1:10.0.0.2:modbus"
