"""Kafka consumer for anomaly results."""

import json
from collections.abc import Iterator
from datetime import datetime

import structlog
from confluent_kafka import Consumer, KafkaError, KafkaException
from pydantic import BaseModel, Field

from src.config import KafkaSettings

logger = structlog.get_logger()


class WindowKey(BaseModel):
    """Window key from anomaly detection."""

    src_ip: str
    dst_ip: str
    protocol: str
    window_size: int
    window_start: int


class AnomalyResult(BaseModel):
    """Anomaly result from the detection service."""

    window_key: WindowKey
    detected_at: datetime
    ensemble_score: float = Field(..., ge=0.0, le=1.0)
    classification: str
    anomaly_type: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    feature_contributions: dict[str, float] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class AnomalyConsumer:
    """Consumes anomaly results from Kafka."""

    def __init__(self, settings: KafkaSettings) -> None:
        """Initialize the consumer."""
        self.settings = settings
        self._consumer: Consumer | None = None

    def connect(self) -> None:
        """Connect to Kafka and subscribe to topic."""
        config = {
            "bootstrap.servers": self.settings.bootstrap_servers,
            "group.id": self.settings.group_id,
            "client.id": self.settings.client_id,
            "auto.offset.reset": self.settings.auto_offset_reset,
            "enable.auto.commit": True,
            "auto.commit.interval.ms": 1000,
        }

        self._consumer = Consumer(config)
        self._consumer.subscribe([self.settings.input_topic])

        logger.info(
            "kafka_consumer_connected",
            topic=self.settings.input_topic,
            group_id=self.settings.group_id,
        )

    def close(self) -> None:
        """Close the consumer connection."""
        if self._consumer:
            self._consumer.close()
            logger.info("kafka_consumer_closed")

    def consume(self, timeout: float = 1.0) -> Iterator[AnomalyResult]:
        """Consume anomaly results from Kafka.

        Yields parsed AnomalyResult objects.
        """
        if not self._consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")

        while True:
            msg = self._consumer.poll(timeout)

            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(msg.error())

            try:
                value = json.loads(msg.value().decode("utf-8"))
                anomaly = AnomalyResult.model_validate(value)
                yield anomaly
            except json.JSONDecodeError as e:
                logger.warning(
                    "message_decode_error",
                    error=str(e),
                    topic=msg.topic(),
                    offset=msg.offset(),
                )
                continue
            except Exception as e:
                logger.warning(
                    "anomaly_parse_error",
                    error=str(e),
                    topic=msg.topic(),
                    offset=msg.offset(),
                )
                continue

    def poll_one(self, timeout: float = 1.0) -> AnomalyResult | None:
        """Poll for a single anomaly result (non-blocking).

        Returns:
            AnomalyResult if available, None otherwise.
        """
        if not self._consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")

        msg = self._consumer.poll(timeout)

        if msg is None:
            return None

        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                return None
            raise KafkaException(msg.error())

        try:
            value = json.loads(msg.value().decode("utf-8"))
            return AnomalyResult.model_validate(value)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("anomaly_parse_error", error=str(e))
            return None

    def __enter__(self) -> "AnomalyConsumer":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()
