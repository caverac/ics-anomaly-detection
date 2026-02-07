"""Sequence builder for LSTM input preparation."""

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger()


@dataclass
class SequenceBuffer:
    """Buffer for accumulating feature vectors into sequences."""

    max_length: int
    vectors: list[np.ndarray] = field(default_factory=list)

    def add(self, vector: np.ndarray) -> None:
        """Add a feature vector to the buffer.

        Args:
            vector: Feature vector of shape (n_features,).
        """
        self.vectors.append(vector)
        if len(self.vectors) > self.max_length:
            self.vectors.pop(0)

    def is_ready(self) -> bool:
        """Check if buffer has enough vectors for a full sequence."""
        return len(self.vectors) >= self.max_length

    def get_sequence(self, pad: bool = True) -> np.ndarray | None:
        """Get the current sequence.

        Args:
            pad: If True, pad incomplete sequences with zeros.

        Returns:
            Sequence array of shape (seq_length, n_features) or None if empty.
        """
        if not self.vectors:
            return None

        if not pad and not self.is_ready():
            return None

        if self.is_ready():
            return np.array(self.vectors[-self.max_length :])

        n_features = self.vectors[0].shape[0]
        padded = np.zeros((self.max_length, n_features))
        n_actual = len(self.vectors)
        padded[-n_actual:] = np.array(self.vectors)
        return padded

    def clear(self) -> None:
        """Clear the buffer."""
        self.vectors.clear()

    def __len__(self) -> int:
        """Get number of vectors in buffer."""
        return len(self.vectors)


class SequenceBuilder:
    """Builds sequences for LSTM from streaming feature vectors.

    Maintains separate buffers per connection (src_ip, dst_ip, protocol)
    to build temporally coherent sequences.
    """

    def __init__(
        self,
        sequence_length: int = 10,
        allow_padding: bool = True,
    ) -> None:
        """Initialize the sequence builder.

        Args:
            sequence_length: Number of feature vectors per sequence.
            allow_padding: If True, allow incomplete sequences with zero padding.
        """
        self.sequence_length = sequence_length
        self.allow_padding = allow_padding
        self._buffers: dict[str, SequenceBuffer] = defaultdict(
            lambda: SequenceBuffer(max_length=self.sequence_length)
        )

    def add_vector(self, connection_key: str, vector: np.ndarray) -> np.ndarray | None:
        """Add a feature vector and return sequence if ready.

        Args:
            connection_key: Unique connection identifier (e.g., "ip1:ip2:proto").
            vector: Feature vector of shape (n_features,).

        Returns:
            Sequence of shape (1, seq_length, n_features) or None.
        """
        buffer = self._buffers[connection_key]
        buffer.add(vector)

        if buffer.is_ready() or (self.allow_padding and len(buffer) > 0):
            sequence = buffer.get_sequence(pad=self.allow_padding)
            if sequence is not None:
                return sequence.reshape(1, self.sequence_length, -1)

        return None

    def get_sequence(self, connection_key: str, pad: bool | None = None) -> np.ndarray | None:
        """Get the current sequence for a connection without adding new data.

        Args:
            connection_key: Unique connection identifier.
            pad: Override for allow_padding. If None, uses instance setting.

        Returns:
            Sequence of shape (1, seq_length, n_features) or None.
        """
        if connection_key not in self._buffers:
            return None

        buffer = self._buffers[connection_key]
        should_pad = pad if pad is not None else self.allow_padding
        sequence = buffer.get_sequence(pad=should_pad)

        if sequence is not None:
            return sequence.reshape(1, self.sequence_length, -1)

        return None

    def clear_connection(self, connection_key: str) -> None:
        """Clear the buffer for a specific connection.

        Args:
            connection_key: Connection to clear.
        """
        if connection_key in self._buffers:
            self._buffers[connection_key].clear()

    def clear_all(self) -> None:
        """Clear all buffers."""
        self._buffers.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about current buffer state.

        Returns:
            Dictionary with buffer statistics.
        """
        buffer_lengths = [len(b) for b in self._buffers.values()]
        ready_count = sum(1 for b in self._buffers.values() if b.is_ready())

        return {
            "total_connections": len(self._buffers),
            "ready_sequences": ready_count,
            "avg_buffer_length": np.mean(buffer_lengths) if buffer_lengths else 0,
            "sequence_length": self.sequence_length,
        }

    def prune_stale(self, min_vectors: int = 1) -> int:
        """Remove connections with too few vectors.

        Args:
            min_vectors: Minimum vectors to keep a connection.

        Returns:
            Number of connections pruned.
        """
        stale_keys = [k for k, b in self._buffers.items() if len(b) < min_vectors]
        for key in stale_keys:
            del self._buffers[key]
        return len(stale_keys)

    def __len__(self) -> int:
        """Get number of active connections."""
        return len(self._buffers)

    def __iter__(self) -> Iterator[str]:
        """Iterate over connection keys."""
        return iter(self._buffers.keys())
