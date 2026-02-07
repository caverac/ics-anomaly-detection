"""Kafka consumer for feature vectors."""

import json
from collections.abc import Iterator
from typing import Any

import structlog
from confluent_kafka import Consumer, KafkaError, KafkaException

from src.config import KafkaSettings
from src.schemas.feature_vector import FeatureVector

logger = structlog.get_logger()


class FeatureConsumer:
    """Consumes feature vectors from Kafka."""

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

    def consume(self, timeout: float = 1.0) -> Iterator[FeatureVector]:
        """Consume feature vectors from Kafka.

        Yields parsed FeatureVector objects.
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
                feature_vector = FeatureVector.model_validate(value)
                yield feature_vector
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
                    "feature_vector_parse_error",
                    error=str(e),
                    topic=msg.topic(),
                    offset=msg.offset(),
                )
                continue

    def __enter__(self) -> "FeatureConsumer":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()
