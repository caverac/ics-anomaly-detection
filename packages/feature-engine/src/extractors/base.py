"""Base feature extractor class."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import numpy as np

from src.windows.manager import WindowBuffer, WindowKey


class BaseExtractor(ABC):
    """Base class for protocol-specific feature extractors."""

    @abstractmethod
    def extract(self, key: WindowKey, buffer: WindowBuffer) -> dict[str, Any]:
        """Extract features from a window buffer.

        Args:
            key: The window key (src_ip, dst_ip, protocol, window info)
            buffer: The buffer containing messages for this window

        Returns:
            Dictionary of extracted features
        """
        pass

    def compute_timing_features(self, timestamps: list[datetime]) -> dict[str, float]:
        """Compute inter-arrival time statistics.

        Args:
            timestamps: List of message timestamps

        Returns:
            Dictionary with IAT statistics
        """
        if len(timestamps) < 2:
            return {
                "iat_mean": 0.0,
                "iat_std": 0.0,
                "iat_min": 0.0,
                "iat_max": 0.0,
                "iat_median": 0.0,
            }

        # Sort timestamps and compute inter-arrival times
        sorted_ts = sorted(timestamps)
        iats = [
            (sorted_ts[i + 1] - sorted_ts[i]).total_seconds()
            for i in range(len(sorted_ts) - 1)
        ]

        iat_array = np.array(iats)

        return {
            "iat_mean": float(np.mean(iat_array)),
            "iat_std": float(np.std(iat_array)),
            "iat_min": float(np.min(iat_array)),
            "iat_max": float(np.max(iat_array)),
            "iat_median": float(np.median(iat_array)),
        }

    def compute_volume_features(self, messages: list[dict[str, Any]]) -> dict[str, float]:
        """Compute volume-based features.

        Args:
            messages: List of messages in the window

        Returns:
            Dictionary with volume statistics
        """
        payload_sizes = [
            msg.get("payload_size", 0) for msg in messages
        ]

        if not payload_sizes:
            return {
                "message_count": 0,
                "bytes_total": 0,
                "bytes_mean": 0.0,
                "bytes_std": 0.0,
                "bytes_min": 0,
                "bytes_max": 0,
            }

        size_array = np.array(payload_sizes)

        return {
            "message_count": len(messages),
            "bytes_total": int(np.sum(size_array)),
            "bytes_mean": float(np.mean(size_array)),
            "bytes_std": float(np.std(size_array)),
            "bytes_min": int(np.min(size_array)),
            "bytes_max": int(np.max(size_array)),
        }


def extract_features(key: WindowKey, buffer: WindowBuffer) -> dict[str, Any]:
    """Extract features from a window using the appropriate extractor.

    Args:
        key: The window key
        buffer: The window buffer

    Returns:
        Feature vector dictionary
    """
    from src.extractors.dnp3 import DNP3Extractor
    from src.extractors.modbus import ModbusExtractor
    from src.extractors.opcua import OPCUAExtractor

    extractors: dict[str, BaseExtractor] = {
        "modbus": ModbusExtractor(),
        "dnp3": DNP3Extractor(),
        "opcua": OPCUAExtractor(),
    }

    extractor = extractors.get(key.protocol.lower())

    if extractor is None:
        # Use generic extraction for unknown protocols
        extractor = ModbusExtractor()  # Fallback

    features = extractor.extract(key, buffer)

    # Add metadata
    features["_window_key"] = {
        "src_ip": key.src_ip,
        "dst_ip": key.dst_ip,
        "protocol": key.protocol,
        "window_size": key.window_size,
        "window_start": key.window_start,
    }
    features["_extracted_at"] = datetime.now().isoformat()

    return features
