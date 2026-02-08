"""Configuration for the alerting service."""

from pydantic import Field
from pydantic_settings import BaseSettings


class KafkaSettings(BaseSettings):
    """Kafka connection settings."""

    bootstrap_servers: str = Field(default="localhost:9092")
    group_id: str = Field(default="alerting")
    client_id: str = Field(default="alerting-client")
    auto_offset_reset: str = Field(default="earliest")

    input_topic: str = Field(default="ics.anomalies")
    output_topic: str = Field(default="ics.alerts")

    model_config = {"env_prefix": "KAFKA_"}


class RedisSettings(BaseSettings):
    """Redis connection settings."""

    url: str = Field(default="redis://localhost:6379")
    db: int = Field(default=0)

    incident_ttl_seconds: int = Field(default=86400)  # 24 hours
    alert_ttl_seconds: int = Field(default=604800)  # 7 days

    model_config = {"env_prefix": "REDIS_"}


class CorrelationSettings(BaseSettings):
    """Correlation engine settings."""

    window_seconds: int = Field(default=300)  # 5 minutes

    model_config = {"env_prefix": "CORRELATION_"}


class DeduplicationSettings(BaseSettings):
    """Deduplication settings."""

    suppression_seconds: int = Field(default=60)

    model_config = {"env_prefix": "DEDUP_"}


class EscalationSettings(BaseSettings):
    """Escalation manager settings."""

    p3_threshold: int = Field(default=5)
    p2_threshold: int = Field(default=10)
    p1_threshold: int = Field(default=20)

    multi_target_escalation: bool = Field(default=True)
    critical_severity_escalation: bool = Field(default=True)

    model_config = {"env_prefix": "ESCALATION_"}


class WebhookSettings(BaseSettings):
    """Webhook notification settings."""

    enabled: bool = Field(default=False)
    url: str = Field(default="")
    timeout_seconds: int = Field(default=10)

    model_config = {"env_prefix": "WEBHOOK_"}


class SlackSettings(BaseSettings):
    """Slack notification settings."""

    enabled: bool = Field(default=False)
    webhook_url: str = Field(default="")
    channel: str = Field(default="#alerts")
    timeout_seconds: int = Field(default=10)

    model_config = {"env_prefix": "SLACK_"}


class SplunkSettings(BaseSettings):
    """Splunk HEC notification settings."""

    enabled: bool = Field(default=False)
    hec_url: str = Field(default="")  # e.g., https://splunk:8088/services/collector/event
    hec_token: str = Field(default="")
    index: str = Field(default="main")
    source: str = Field(default="ics-alerting")
    sourcetype: str = Field(default="ics:alerts")
    verify_ssl: bool = Field(default=True)
    timeout_seconds: int = Field(default=10)

    model_config = {"env_prefix": "SPLUNK_"}


class SyslogSettings(BaseSettings):
    """Syslog notification settings."""

    enabled: bool = Field(default=False)
    host: str = Field(default="")
    port: int = Field(default=514)
    protocol: str = Field(default="udp")  # udp or tcp
    facility: str = Field(default="LOCAL0")  # LOCAL0-LOCAL7
    hostname: str = Field(default="")  # Override hostname in syslog message
    timeout_seconds: int = Field(default=5)

    model_config = {"env_prefix": "SYSLOG_"}


class ApiSettings(BaseSettings):
    """API server settings."""

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8084)

    model_config = {"env_prefix": "API_"}


class Settings(BaseSettings):
    """Main application settings."""

    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    correlation: CorrelationSettings = Field(default_factory=CorrelationSettings)
    deduplication: DeduplicationSettings = Field(default_factory=DeduplicationSettings)
    escalation: EscalationSettings = Field(default_factory=EscalationSettings)
    webhook: WebhookSettings = Field(default_factory=WebhookSettings)
    slack: SlackSettings = Field(default_factory=SlackSettings)
    splunk: SplunkSettings = Field(default_factory=SplunkSettings)
    syslog: SyslogSettings = Field(default_factory=SyslogSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)

    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    model_config = {"env_prefix": "ALERTING_"}


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
