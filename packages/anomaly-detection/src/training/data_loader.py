"""Data loading utilities for training."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import structlog
from confluent_kafka import Consumer, KafkaError, KafkaException

from src.config import KafkaSettings, TrainingSettings
from src.schemas.feature_vector import FeatureVector

logger = structlog.get_logger()


class TrainingDataLoader:
    """Load training data from Kafka or files.

    Supports loading historical feature vectors from Kafka topics
    or from JSON/npy files on disk.
    """

    def __init__(self, settings: TrainingSettings) -> None:
        """Initialize the data loader.

        Args:
            settings: Training configuration.
        """
        self.settings = settings
        self.data_dir = settings.data_dir

    def load_from_kafka(
        self,
        kafka_settings: KafkaSettings,
        max_messages: int = 10000,
        timeout_seconds: float = 60.0,
    ) -> tuple[list[FeatureVector], list[str]]:
        """Load feature vectors from Kafka topic.

        Consumes from the beginning of the topic up to max_messages.

        Args:
            kafka_settings: Kafka connection settings.
            max_messages: Maximum messages to consume.
            timeout_seconds: Total timeout for consumption.

        Returns:
            Tuple of (feature_vectors, feature_names).
        """
        config = {
            "bootstrap.servers": kafka_settings.bootstrap_servers,
            "group.id": f"training-loader-{int(np.random.rand() * 10000)}",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }

        consumer = Consumer(config)
        consumer.subscribe([kafka_settings.input_topic])

        vectors: list[FeatureVector] = []
        feature_names: list[str] = []
        empty_polls = 0
        max_empty_polls = int(timeout_seconds / 1.0)

        logger.info(
            "loading_from_kafka",
            topic=kafka_settings.input_topic,
            max_messages=max_messages,
        )

        try:
            while len(vectors) < max_messages and empty_polls < max_empty_polls:
                msg = consumer.poll(1.0)

                if msg is None:
                    empty_polls += 1
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        empty_polls += 1
                        continue
                    raise KafkaException(msg.error())

                empty_polls = 0

                try:
                    value = json.loads(msg.value().decode("utf-8"))
                    vector = FeatureVector.model_validate(value)
                    vectors.append(vector)

                    if not feature_names:
                        feature_names = vector.get_feature_names()

                except Exception as e:
                    logger.warning("parse_error", error=str(e))
                    continue

        finally:
            consumer.close()

        logger.info("kafka_loading_complete", vectors_loaded=len(vectors))
        return vectors, feature_names

    def load_from_file(self, path: Path) -> tuple[np.ndarray, list[str]]:
        """Load feature data from file.

        Supports JSON and NPY formats.

        Args:
            path: Path to data file.

        Returns:
            Tuple of (feature_array, feature_names).
        """
        if path.suffix == ".npy":
            data = np.load(path, allow_pickle=True).item()
            return data["features"], data["feature_names"]

        elif path.suffix == ".json":
            with open(path) as f:
                records = json.load(f)

            vectors = [FeatureVector.model_validate(r) for r in records]
            feature_names = vectors[0].get_feature_names() if vectors else []

            features_list = [list(v.to_ml_input().values()) for v in vectors]
            return np.array(features_list), feature_names

        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def load_from_directory(self, pattern: str = "*.json") -> tuple[np.ndarray, list[str]]:
        """Load all data files from directory.

        Args:
            pattern: Glob pattern for files.

        Returns:
            Tuple of (combined_features, feature_names).
        """
        all_features: list[np.ndarray] = []
        feature_names: list[str] = []

        for path in sorted(self.data_dir.glob(pattern)):
            features, names = self.load_from_file(path)
            all_features.append(features)
            if not feature_names:
                feature_names = names

        if not all_features:
            raise ValueError(f"No data files found in {self.data_dir}")

        combined = np.vstack(all_features)
        logger.info(
            "directory_loading_complete",
            total_samples=combined.shape[0],
            n_features=combined.shape[1],
        )
        return combined, feature_names

    def vectors_to_array(
        self, vectors: list[FeatureVector]
    ) -> tuple[np.ndarray, list[str]]:
        """Convert feature vectors to numpy array.

        Args:
            vectors: List of feature vectors.

        Returns:
            Tuple of (feature_array, feature_names).
        """
        if not vectors:
            return np.array([]), []

        feature_names = vectors[0].get_feature_names()
        features_list = []

        for v in vectors:
            ml_input = v.to_ml_input()
            row = [ml_input.get(name, 0.0) for name in feature_names]
            features_list.append(row)

        return np.array(features_list), feature_names

    def build_sequences(
        self,
        features: np.ndarray,
        sequence_length: int = 10,
        stride: int = 1,
    ) -> np.ndarray:
        """Build sequences for LSTM training.

        Creates overlapping sequences using sliding window.

        Args:
            features: Feature array of shape (n_samples, n_features).
            sequence_length: Length of each sequence.
            stride: Step size between sequences.

        Returns:
            Sequences of shape (n_sequences, sequence_length, n_features).
        """
        n_samples, n_features = features.shape

        if n_samples < sequence_length:
            padded = np.zeros((sequence_length, n_features))
            padded[-n_samples:] = features
            return padded.reshape(1, sequence_length, n_features)

        n_sequences = (n_samples - sequence_length) // stride + 1
        sequences = np.zeros((n_sequences, sequence_length, n_features))

        for i in range(n_sequences):
            start = i * stride
            sequences[i] = features[start : start + sequence_length]

        logger.info(
            "sequences_built",
            n_sequences=n_sequences,
            sequence_length=sequence_length,
        )
        return sequences

    def save_training_data(
        self,
        features: np.ndarray,
        feature_names: list[str],
        path: Path,
    ) -> None:
        """Save training data to disk.

        Args:
            features: Feature array.
            feature_names: List of feature names.
            path: Output path.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(
            path,
            {"features": features, "feature_names": feature_names},
            allow_pickle=True,
        )
        logger.info("training_data_saved", path=str(path), samples=features.shape[0])
