"""Kafka components for the alerting service."""

from src.kafka.consumer import AnomalyConsumer
from src.kafka.producer import AlertProducer

__all__ = ["AnomalyConsumer", "AlertProducer"]
