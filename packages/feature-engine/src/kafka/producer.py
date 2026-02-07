"""Kafka producer for feature vectors."""

import json
from typing import Any

import structlog
from confluent_kafka import Producer

from src.config import KafkaSettings

logger = structlog.get_logger()


class FeatureProducer:
    """Produces feature vectors to Kafka."""

    def __init__(self, settings: KafkaSettings) -> None:
        """Initialize the producer."""
        self.settings = settings
        self._producer: Producer | None = None
        self._delivery_count = 0
        self._error_count = 0

    def connect(self) -> None:
        """Connect to Kafka."""
        config = {
            "bootstrap.servers": self.settings.bootstrap_servers,
            "client.id": f"{self.settings.client_id}-producer",
            "compression.type": "gzip",
            "batch.size": 16384,
            "linger.ms": 5,
        }

        self._producer = Producer(config)
        logger.info("kafka_producer_connected")

    def close(self) -> None:
        """Flush and close the producer."""
        if self._producer:
            self._producer.flush(timeout=10)
            logger.info(
                "kafka_producer_closed",
                delivered=self._delivery_count,
                errors=self._error_count,
            )

    def _delivery_callback(self, err: Any, msg: Any) -> None:
        """Handle delivery reports."""
        if err:
            self._error_count += 1
            logger.error("message_delivery_failed", error=str(err))
        else:
            self._delivery_count += 1

    def produce(self, key: str, value: dict[str, Any]) -> None:
        """Produce a feature vector to Kafka.

        Args:
            key: Message key (typically src_ip:dst_ip)
            value: Feature vector dictionary
        """
        if not self._producer:
            raise RuntimeError("Producer not connected. Call connect() first.")

        self._producer.produce(
            topic=self.settings.output_topic,
            key=key.encode("utf-8"),
            value=json.dumps(value).encode("utf-8"),
            callback=self._delivery_callback,
        )

        # Trigger delivery callbacks
        self._producer.poll(0)

    def flush(self) -> None:
        """Flush pending messages."""
        if self._producer:
            self._producer.flush(timeout=5)

    def __enter__(self) -> "FeatureProducer":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()
