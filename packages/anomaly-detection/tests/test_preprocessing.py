"""Tests for preprocessing components."""

import numpy as np
import pytest

from src.preprocessing.normalizer import FeatureNormalizer
from src.preprocessing.sequence_builder import SequenceBuilder


class TestFeatureNormalizer:
    """Tests for feature normalizer."""

    def test_fit_transform(self) -> None:
        """Test normalizer fits and transforms data."""
        normalizer = FeatureNormalizer()

        X = np.array([[1.0, 100.0], [2.0, 200.0], [3.0, 300.0]])
        X_normalized = normalizer.fit_transform(X, ["a", "b"])

        assert normalizer.is_fitted
        assert normalizer.feature_names == ["a", "b"]

        assert np.abs(X_normalized.mean(axis=0)).max() < 1e-10
        assert np.abs(X_normalized.std(axis=0) - 1.0).max() < 1e-10

    def test_transform_without_fit(self) -> None:
        """Test transform raises error without fit."""
        normalizer = FeatureNormalizer()

        with pytest.raises(RuntimeError):
            normalizer.transform(np.array([[1.0, 2.0]]))

    def test_get_stats(self) -> None:
        """Test statistics extraction."""
        normalizer = FeatureNormalizer()

        X = np.array([[0.0, 0.0], [10.0, 100.0]])
        normalizer.fit(X, ["x", "y"])

        stats = normalizer.get_stats()
        assert "mean" in stats
        assert "std" in stats
        assert stats["mean"]["x"] == 5.0
        assert stats["mean"]["y"] == 50.0


class TestSequenceBuilder:
    """Tests for sequence builder."""

    def test_build_sequence(self) -> None:
        """Test sequence building from vectors."""
        builder = SequenceBuilder(sequence_length=3, allow_padding=True)

        for i in range(3):
            vector = np.array([float(i), float(i) * 2])
            result = builder.add_vector("conn1", vector)

        assert result is not None
        assert result.shape == (1, 3, 2)

    def test_padded_sequence(self) -> None:
        """Test padding for incomplete sequences."""
        builder = SequenceBuilder(sequence_length=5, allow_padding=True)

        vector = np.array([1.0, 2.0, 3.0])
        result = builder.add_vector("conn1", vector)

        assert result is not None
        assert result.shape == (1, 5, 3)
        assert np.sum(result[0, :4, :]) == 0

    def test_separate_connections(self) -> None:
        """Test separate buffers per connection."""
        builder = SequenceBuilder(sequence_length=2)

        builder.add_vector("conn1", np.array([1.0]))
        builder.add_vector("conn2", np.array([2.0]))
        builder.add_vector("conn1", np.array([3.0]))

        seq1 = builder.get_sequence("conn1")
        seq2 = builder.get_sequence("conn2")

        assert seq1 is not None
        assert seq2 is not None
        assert seq1[0, -1, 0] == 3.0
        assert seq2[0, -1, 0] == 2.0

    def test_stats(self) -> None:
        """Test stats reporting."""
        builder = SequenceBuilder(sequence_length=3)

        builder.add_vector("conn1", np.array([1.0]))
        builder.add_vector("conn1", np.array([2.0]))
        builder.add_vector("conn1", np.array([3.0]))
        builder.add_vector("conn2", np.array([1.0]))

        stats = builder.get_stats()
        assert stats["total_connections"] == 2
        assert stats["ready_sequences"] == 1
        assert stats["sequence_length"] == 3
