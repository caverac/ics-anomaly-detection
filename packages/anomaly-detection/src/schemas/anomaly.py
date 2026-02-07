"""Anomaly detection output schema."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Classification(str, Enum):
    """Anomaly classification levels."""

    NORMAL = "normal"
    SUSPICIOUS = "suspicious"
    ANOMALY = "anomaly"
    CRITICAL = "critical"


class AnomalyType(str, Enum):
    """Types of anomalies detected in ICS traffic."""

    UNKNOWN = "unknown"
    RECONNAISSANCE = "reconnaissance"
    TIMING_ANOMALY = "timing_anomaly"
    VOLUME_ANOMALY = "volume_anomaly"
    PROTOCOL_VIOLATION = "protocol_violation"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_EXFILTRATION = "data_exfiltration"
    COMMAND_INJECTION = "command_injection"


class ModelScore(BaseModel):
    """Score from an individual model."""

    model_name: str
    score: float = Field(..., ge=0.0, le=1.0)
    weight: float = Field(..., ge=0.0, le=1.0)
    raw_score: float
    inference_time_ms: float


class WindowKey(BaseModel):
    """Window key for identifying the source data."""

    src_ip: str
    dst_ip: str
    protocol: str
    window_size: int
    window_start: int


class AnomalyResult(BaseModel):
    """Result from the anomaly detection ensemble."""

    window_key: WindowKey
    detected_at: datetime = Field(default_factory=datetime.utcnow)

    model_scores: list[ModelScore] = Field(default_factory=list)

    ensemble_score: float = Field(..., ge=0.0, le=1.0)
    classification: Classification
    anomaly_type: AnomalyType | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)

    feature_contributions: dict[str, float] = Field(default_factory=dict)

    def to_kafka_message(self) -> dict[str, Any]:
        """Convert to Kafka message format."""
        return self.model_dump(mode="json")

    def get_message_key(self) -> str:
        """Get Kafka message key."""
        return f"{self.window_key.src_ip}:{self.window_key.dst_ip}:{self.window_key.protocol}"
