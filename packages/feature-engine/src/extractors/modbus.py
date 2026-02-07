"""Modbus-specific feature extractor."""

from collections import Counter
from datetime import datetime
from typing import Any

import numpy as np

from src.extractors.base import BaseExtractor
from src.windows.manager import WindowBuffer, WindowKey


class ModbusExtractor(BaseExtractor):
    """Extract features from Modbus messages."""

    # Modbus function codes
    READ_FUNCTIONS = {1, 2, 3, 4}  # Read coils, discrete inputs, holding/input registers
    WRITE_FUNCTIONS = {5, 6, 15, 16}  # Write single/multiple coils/registers
    DIAGNOSTIC_FUNCTIONS = {7, 8, 11, 12, 17}  # Diagnostic functions

    def extract(self, key: WindowKey, buffer: WindowBuffer) -> dict[str, Any]:
        """Extract Modbus-specific features."""
        messages = buffer.messages
        timestamps = self._get_timestamps(messages)

        # Base features
        features: dict[str, Any] = {
            "protocol": "modbus",
            "window_size_seconds": key.window_size,
        }

        # Volume features
        features.update(self.compute_volume_features(messages))

        # Timing features
        features.update(self.compute_timing_features(timestamps))

        # Modbus-specific features
        features.update(self._extract_function_code_features(messages))
        features.update(self._extract_unit_id_features(messages))
        features.update(self._extract_address_features(messages))
        features.update(self._extract_exception_features(messages))
        features.update(self._extract_request_response_features(messages))

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

    def _extract_function_code_features(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract function code distribution features."""
        # Get function codes from messages - check both direct and nested structures
        function_codes = []
        for msg in messages:
            fc = msg.get("function_code")
            if fc is None and "message" in msg:
                fc = msg["message"].get("function_code")
            if fc is not None:
                function_codes.append(fc)

        if not function_codes:
            return {
                "fc_unique_count": 0,
                "fc_read_ratio": 0.0,
                "fc_write_ratio": 0.0,
                "fc_diagnostic_ratio": 0.0,
                "fc_entropy": 0.0,
                "fc_most_common": 0,
                "fc_most_common_ratio": 0.0,
            }

        counter = Counter(function_codes)
        total = len(function_codes)

        # Count by category
        read_count = sum(counter.get(fc, 0) for fc in self.READ_FUNCTIONS)
        write_count = sum(counter.get(fc, 0) for fc in self.WRITE_FUNCTIONS)
        diag_count = sum(counter.get(fc, 0) for fc in self.DIAGNOSTIC_FUNCTIONS)

        # Compute entropy
        probs = np.array(list(counter.values())) / total
        entropy = float(-np.sum(probs * np.log2(probs + 1e-10)))

        most_common_fc, most_common_count = counter.most_common(1)[0]

        return {
            "fc_unique_count": len(counter),
            "fc_read_ratio": read_count / total,
            "fc_write_ratio": write_count / total,
            "fc_diagnostic_ratio": diag_count / total,
            "fc_entropy": entropy,
            "fc_most_common": most_common_fc,
            "fc_most_common_ratio": most_common_count / total,
        }

    def _extract_unit_id_features(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract unit ID distribution features."""
        unit_ids = []
        for msg in messages:
            uid = msg.get("unit_id")
            if uid is None and "message" in msg:
                uid = msg["message"].get("unit_id")
            if uid is not None:
                unit_ids.append(uid)

        if not unit_ids:
            return {
                "unit_id_unique_count": 0,
                "unit_id_entropy": 0.0,
            }

        counter = Counter(unit_ids)
        total = len(unit_ids)

        probs = np.array(list(counter.values())) / total
        entropy = float(-np.sum(probs * np.log2(probs + 1e-10)))

        return {
            "unit_id_unique_count": len(counter),
            "unit_id_entropy": entropy,
        }

    def _extract_address_features(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract register/coil address access patterns."""
        start_addresses: list[int] = []
        quantities: list[int] = []

        for msg in messages:
            data = msg.get("message", msg)
            if "start_address" in data:
                start_addresses.append(data["start_address"])
            if "quantity" in data:
                quantities.append(data["quantity"])

        features: dict[str, Any] = {}

        if start_addresses:
            addr_array = np.array(start_addresses)
            features["addr_unique_count"] = len(set(start_addresses))
            features["addr_mean"] = float(np.mean(addr_array))
            features["addr_std"] = float(np.std(addr_array))
            features["addr_min"] = int(np.min(addr_array))
            features["addr_max"] = int(np.max(addr_array))
            features["addr_range"] = int(np.max(addr_array) - np.min(addr_array))
        else:
            features["addr_unique_count"] = 0
            features["addr_mean"] = 0.0
            features["addr_std"] = 0.0
            features["addr_min"] = 0
            features["addr_max"] = 0
            features["addr_range"] = 0

        if quantities:
            qty_array = np.array(quantities)
            features["qty_mean"] = float(np.mean(qty_array))
            features["qty_max"] = int(np.max(qty_array))
        else:
            features["qty_mean"] = 0.0
            features["qty_max"] = 0

        return features

    def _extract_exception_features(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract exception/error features."""
        exception_count = 0
        exception_codes: list[int] = []

        for msg in messages:
            data = msg.get("message", msg)
            if data.get("is_exception"):
                exception_count += 1
                if "exception_code" in data:
                    exception_codes.append(data["exception_code"])

        return {
            "exception_count": exception_count,
            "exception_ratio": exception_count / len(messages) if messages else 0.0,
            "exception_codes_unique": len(set(exception_codes)),
        }

    def _extract_request_response_features(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract request/response pattern features."""
        request_count = 0
        response_count = 0

        for msg in messages:
            data = msg.get("message", msg)
            # Determine if request or response based on is_exception flag or port
            if data.get("is_exception"):
                response_count += 1
            elif msg.get("dst_port") == 502:
                request_count += 1
            else:
                response_count += 1

        total = request_count + response_count
        return {
            "request_count": request_count,
            "response_count": response_count,
            "request_ratio": request_count / total if total > 0 else 0.5,
        }
