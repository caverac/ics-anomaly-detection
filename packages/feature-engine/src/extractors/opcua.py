"""OPC-UA specific feature extractor."""

from collections import Counter
from datetime import datetime
from typing import Any

import numpy as np

from src.extractors.base import BaseExtractor
from src.windows.manager import WindowBuffer, WindowKey


class OPCUAExtractor(BaseExtractor):
    """Extract features from OPC-UA messages."""

    # OPC-UA message types
    HANDSHAKE_TYPES = {"Hello", "Acknowledge", "OpenSecureChannel", "CloseSecureChannel"}
    DATA_TYPES = {"Message"}
    ERROR_TYPES = {"Error"}

    def extract(self, key: WindowKey, buffer: WindowBuffer) -> dict[str, Any]:
        """Extract OPC-UA specific features."""
        messages = buffer.messages
        timestamps = self._get_timestamps(messages)

        # Base features
        features: dict[str, Any] = {
            "protocol": "opcua",
            "window_size_seconds": key.window_size,
        }

        # Volume features
        features.update(self.compute_volume_features(messages))

        # Timing features
        features.update(self.compute_timing_features(timestamps))

        # OPC-UA specific features
        features.update(self._extract_message_type_features(messages))
        features.update(self._extract_channel_features(messages))
        features.update(self._extract_service_features(messages))

        return features

    def _get_timestamps(self, messages: list[dict[str, Any]]) -> list[datetime]:
        """Extract timestamps from messages."""
        timestamps = []
        for msg in messages:
            ts_str = msg.get("timestamp", "")
            if ts_str:
                try:
                    ts = ts_str.replace("Z", "+00:00")
                    timestamps.append(datetime.fromisoformat(ts))
                except ValueError:
                    pass
        return timestamps

    def _extract_message_type_features(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract message type distribution features."""
        message_types = []
        for msg in messages:
            data = msg.get("message", msg)
            msg_type = data.get("message_type")
            if msg_type:
                message_types.append(msg_type)

        if not message_types:
            return {
                "msg_type_unique": 0,
                "msg_handshake_ratio": 0.0,
                "msg_data_ratio": 0.0,
                "msg_error_ratio": 0.0,
                "msg_type_entropy": 0.0,
            }

        counter = Counter(message_types)
        total = len(message_types)

        handshake_count = sum(counter.get(t, 0) for t in self.HANDSHAKE_TYPES)
        data_count = sum(counter.get(t, 0) for t in self.DATA_TYPES)
        error_count = sum(counter.get(t, 0) for t in self.ERROR_TYPES)

        probs = np.array(list(counter.values())) / total
        entropy = float(-np.sum(probs * np.log2(probs + 1e-10)))

        return {
            "msg_type_unique": len(counter),
            "msg_handshake_ratio": handshake_count / total,
            "msg_data_ratio": data_count / total,
            "msg_error_ratio": error_count / total,
            "msg_type_entropy": entropy,
        }

    def _extract_channel_features(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract secure channel features."""
        channel_ids: list[int] = []
        token_ids: list[int] = []

        for msg in messages:
            data = msg.get("message", msg)
            if "secure_channel_id" in data and data["secure_channel_id"]:
                channel_ids.append(data["secure_channel_id"])
            if "security_token_id" in data and data["security_token_id"]:
                token_ids.append(data["security_token_id"])

        return {
            "channel_unique": len(set(channel_ids)),
            "token_unique": len(set(token_ids)),
            "channel_reuse_ratio": 1 - (len(set(channel_ids)) / len(channel_ids))
            if channel_ids
            else 0.0,
        }

    def _extract_service_features(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract service type features."""
        service_types: list[str] = []
        sequence_numbers: list[int] = []

        for msg in messages:
            data = msg.get("message", msg)
            if "service_type" in data and data["service_type"]:
                service_types.append(data["service_type"])
            if "sequence_number" in data and data["sequence_number"]:
                sequence_numbers.append(data["sequence_number"])

        service_counter = Counter(service_types)

        # Compute sequence number gaps (potential missed messages)
        seq_gaps = 0
        if len(sequence_numbers) > 1:
            sorted_seqs = sorted(sequence_numbers)
            for i in range(1, len(sorted_seqs)):
                gap = sorted_seqs[i] - sorted_seqs[i - 1]
                if gap > 1:
                    seq_gaps += gap - 1

        return {
            "service_unique": len(service_counter),
            "service_open_channel": service_counter.get("OpenSecureChannel", 0),
            "service_close_channel": service_counter.get("CloseSecureChannel", 0),
            "service_error": service_counter.get("Error", 0),
            "sequence_gaps": seq_gaps,
        }
