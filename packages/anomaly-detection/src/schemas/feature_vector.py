"""Feature vector input schema (from feature-engine)."""

from datetime import datetime

from pydantic import BaseModel, Field


class WindowMetadata(BaseModel):
    """Metadata about the time window."""

    src_ip: str
    dst_ip: str
    protocol: str
    window_size: int
    window_start: int


class FeatureVector(BaseModel):
    """Feature vector from the feature-engine."""

    window_key: WindowMetadata = Field(..., alias="_window_key")
    extracted_at: datetime = Field(..., alias="_extracted_at")

    protocol: str
    window_size_seconds: int

    message_count: int = 0
    bytes_total: int = 0
    bytes_mean: float = 0.0
    bytes_std: float = 0.0
    bytes_min: int = 0
    bytes_max: int = 0

    iat_mean: float = 0.0
    iat_std: float = 0.0
    iat_min: float = 0.0
    iat_max: float = 0.0
    iat_median: float = 0.0

    model_config = {"extra": "allow", "populate_by_name": True}

    def to_ml_input(self) -> dict[str, float | int]:
        """Convert to a flat dictionary suitable for ML model input."""
        result: dict[str, float | int] = {}

        for key, value in self.model_dump(by_alias=False).items():
            if key.startswith("_") or key in ("window_key", "extracted_at", "protocol"):
                continue
            if isinstance(value, (int, float)):
                result[key] = value

        return result

    def get_feature_names(self) -> list[str]:
        """Get list of feature names for ML input."""
        return sorted(self.to_ml_input().keys())

    def get_connection_key(self) -> str:
        """Get unique connection identifier."""
        return f"{self.window_key.src_ip}:{self.window_key.dst_ip}:{self.window_key.protocol}"
