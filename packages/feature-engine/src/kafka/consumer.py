"""Kafka consumer for parsed ICS messages."""

import json
from collections.abc import Iterator
from typing import Any

import structlog
from confluent_kafka import Consumer, KafkaError, KafkaException

from src.config import KafkaSettings

logger = structlog.get_logger()


class MessageConsumer:
    """Consumes parsed ICS messages from Kafka."""

    def __init__(self, settings: KafkaSettings) -> None:
        """Initialize the consumer."""
        self.settings = settings
        self._consumer: Consumer | None = None

    def connect(self) -> None:
        """Connect to Kafka and subscribe to topics."""
        config = {
            "bootstrap.servers": self.settings.bootstrap_servers,
            "group.id": self.settings.group_id,
            "client.id": self.settings.client_id,
            "auto.offset.reset": self.settings.auto_offset_reset,
            "enable.auto.commit": True,
            "auto.commit.interval.ms": 1000,
        }

        self._consumer = Consumer(config)
        self._consumer.subscribe(self.settings.input_topics)

        logger.info(
            "kafka_consumer_connected",
            topics=self.settings.input_topics,
            group_id=self.settings.group_id,
        )

    def close(self) -> None:
        """Close the consumer connection."""
        if self._consumer:
            self._consumer.close()
            logger.info("kafka_consumer_closed")

    def consume(self, timeout: float = 1.0) -> Iterator[dict[str, Any]]:
        """Consume messages from Kafka.

        Yields parsed message dictionaries.
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
                value["_topic"] = msg.topic()
                value["_partition"] = msg.partition()
                value["_offset"] = msg.offset()
                yield value
            except json.JSONDecodeError as e:
                logger.warning(
                    "message_decode_error",
                    error=str(e),
                    topic=msg.topic(),
                    offset=msg.offset(),
                )
                continue

    def __enter__(self) -> "MessageConsumer":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()
