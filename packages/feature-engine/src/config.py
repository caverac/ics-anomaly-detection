"""Configuration for the feature engine."""

from pydantic import Field
from pydantic_settings import BaseSettings


class KafkaSettings(BaseSettings):
    """Kafka connection settings."""

    bootstrap_servers: str = Field(default="localhost:9092")
    group_id: str = Field(default="feature-engine")
    client_id: str = Field(default="feature-engine-client")
    auto_offset_reset: str = Field(default="earliest")

    # Input topics (consume parsed messages from parser)
    input_topics: list[str] = Field(
        default=["ics.parsed.modbus", "ics.parsed.dnp3", "ics.parsed.opcua"]
    )

    # Output topic
    output_topic: str = Field(default="ics.features")

    model_config = {"env_prefix": "KAFKA_"}


class WindowSettings(BaseSettings):
    """Window configuration for feature aggregation."""

    # Window durations in seconds
    window_sizes: list[int] = Field(default=[60, 300, 900])  # 1m, 5m, 15m

    # How often to emit features (seconds)
    emit_interval: int = Field(default=60)

    # Max messages to buffer per window
    max_buffer_size: int = Field(default=100000)

    model_config = {"env_prefix": "WINDOW_"}


class Settings(BaseSettings):
    """Main application settings."""

    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    windows: WindowSettings = Field(default_factory=WindowSettings)

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")  # "json" or "console"

    model_config = {"env_prefix": "FEATURE_ENGINE_"}


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
