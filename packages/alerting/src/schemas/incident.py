"""Incident schema for correlating alerts."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IncidentStatus(str, Enum):
    """Incident status."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class IncidentPriority(str, Enum):
    """Incident priority levels."""

    P4 = "P4"  # Low
    P3 = "P3"  # Medium
    P2 = "P2"  # High
    P1 = "P1"  # Critical


class Incident(BaseModel):
    """Incident representing correlated anomalies."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_key: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    status: IncidentStatus = IncidentStatus.ACTIVE
    priority: IncidentPriority = IncidentPriority.P4

    anomaly_count: int = Field(default=0, ge=0)
    alert_ids: list[str] = Field(default_factory=list)

    max_ensemble_score: float = Field(default=0.0, ge=0.0, le=1.0)
    src_ips: list[str] = Field(default_factory=list)
    dst_ips: list[str] = Field(default_factory=list)
    anomaly_types: list[str] = Field(default_factory=list)

    title: str = ""
    description: str = ""

    def add_anomaly(
        self,
        alert_id: str,
        ensemble_score: float,
        src_ip: str,
        dst_ip: str,
        anomaly_type: str | None,
    ) -> None:
        """Add an anomaly to this incident."""
        self.anomaly_count += 1
        self.alert_ids.append(alert_id)
        self.updated_at = datetime.utcnow()

        if ensemble_score > self.max_ensemble_score:
            self.max_ensemble_score = ensemble_score

        if src_ip not in self.src_ips:
            self.src_ips.append(src_ip)

        if dst_ip not in self.dst_ips:
            self.dst_ips.append(dst_ip)

        if anomaly_type and anomaly_type not in self.anomaly_types:
            self.anomaly_types.append(anomaly_type)

    def is_multi_source(self) -> bool:
        """Check if incident involves multiple source IPs."""
        return len(self.src_ips) > 1

    def is_multi_target(self) -> bool:
        """Check if incident involves multiple target IPs."""
        return len(self.dst_ips) > 1

    @classmethod
    def from_redis(cls, data: dict[str, Any]) -> "Incident":
        """Create an Incident from Redis-stored data."""
        return cls.model_validate(data)

    def to_redis(self) -> dict[str, Any]:
        """Convert to format for Redis storage."""
        return self.model_dump(mode="json")

    @staticmethod
    def generate_correlation_key(src_ip: str, dst_ip: str, protocol: str) -> str:
        """Generate a correlation key from connection details."""
        return f"{src_ip}:{dst_ip}:{protocol}"
