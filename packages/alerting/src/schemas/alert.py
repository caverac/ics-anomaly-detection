"""Alert schema for the alerting service."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status."""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertSource(BaseModel):
    """Source information for an alert."""

    src_ip: str
    dst_ip: str
    protocol: str
    window_size: int
    window_start: int


class Alert(BaseModel):
    """Alert generated from anomaly detection."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    incident_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    severity: AlertSeverity
    status: AlertStatus = AlertStatus.OPEN
    title: str
    description: str

    source: AlertSource
    anomaly_type: str | None = None
    ensemble_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    related_anomaly_count: int = Field(default=1, ge=1)

    feature_contributions: dict[str, float] = Field(default_factory=dict)

    def to_kafka_message(self) -> dict[str, Any]:
        """Convert to Kafka message format."""
        return self.model_dump(mode="json")

    def get_message_key(self) -> str:
        """Get Kafka message key for partitioning."""
        return f"{self.source.src_ip}:{self.source.dst_ip}:{self.source.protocol}"

    def get_dedup_key(self) -> str:
        """Get key for deduplication."""
        return f"{self.source.src_ip}:{self.source.dst_ip}:{self.source.protocol}:{self.anomaly_type}"

    @classmethod
    def from_redis(cls, data: dict[str, Any]) -> "Alert":
        """Create an Alert from Redis-stored data."""
        return cls.model_validate(data)

    def to_redis(self) -> dict[str, Any]:
        """Convert to format for Redis storage."""
        return self.model_dump(mode="json")
