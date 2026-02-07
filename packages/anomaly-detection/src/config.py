"""Configuration for the anomaly detection service."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class KafkaSettings(BaseSettings):
    """Kafka connection settings."""

    bootstrap_servers: str = Field(default="localhost:9092")
    group_id: str = Field(default="anomaly-detection")
    client_id: str = Field(default="anomaly-detection-client")
    auto_offset_reset: str = Field(default="earliest")

    input_topic: str = Field(default="ics.features")
    output_topic: str = Field(default="ics.anomalies")

    model_config = {"env_prefix": "KAFKA_"}


class ModelSettings(BaseSettings):
    """Model configuration settings."""

    model_dir: Path = Field(default=Path("/app/models"))

    isolation_forest_weight: float = Field(default=0.3)
    lstm_autoencoder_weight: float = Field(default=0.5)
    one_class_svm_weight: float = Field(default=0.2)

    suspicious_threshold: float = Field(default=0.4)
    anomaly_threshold: float = Field(default=0.7)
    critical_threshold: float = Field(default=0.9)

    lstm_sequence_length: int = Field(default=10)
    lstm_hidden_size: int = Field(default=64)
    lstm_num_layers: int = Field(default=2)

    hot_reload_enabled: bool = Field(default=True)
    hot_reload_interval_seconds: int = Field(default=30)

    model_config = {"env_prefix": "MODEL_"}


class TrainingSettings(BaseSettings):
    """Training configuration settings."""

    data_dir: Path = Field(default=Path("/app/data"))
    output_dir: Path = Field(default=Path("/app/models"))

    epochs: int = Field(default=50)
    batch_size: int = Field(default=32)
    learning_rate: float = Field(default=0.001)
    validation_split: float = Field(default=0.2)

    isolation_forest_n_estimators: int = Field(default=100)
    isolation_forest_contamination: float = Field(default=0.1)

    svm_nu: float = Field(default=0.1)
    svm_kernel: str = Field(default="rbf")
    svm_gamma: str = Field(default="scale")

    mlflow_tracking_uri: str = Field(default="http://localhost:5000")
    mlflow_experiment_name: str = Field(default="ics-anomaly-detection")

    model_config = {"env_prefix": "TRAINING_"}


class Settings(BaseSettings):
    """Main application settings."""

    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    model: ModelSettings = Field(default_factory=ModelSettings)
    training: TrainingSettings = Field(default_factory=TrainingSettings)

    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    model_config = {"env_prefix": "ANOMALY_DETECTION_"}


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
