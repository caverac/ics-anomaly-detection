"""DNP3-specific feature extractor."""

from collections import Counter
from datetime import datetime
from typing import Any

import numpy as np

from src.extractors.base import BaseExtractor
from src.windows.manager import WindowBuffer, WindowKey


class DNP3Extractor(BaseExtractor):
    """Extract features from DNP3 messages."""

    # DNP3 application function codes
    READ_FUNCTIONS = {0x01}  # Read
    WRITE_FUNCTIONS = {0x02, 0x03, 0x04, 0x05, 0x06}  # Write, Select, Operate, etc.
    CONTROL_FUNCTIONS = {0x0D, 0x0E}  # Cold/Warm restart
    RESPONSE_FUNCTIONS = {0x81, 0x82}  # Response, Unsolicited Response

    def extract(self, key: WindowKey, buffer: WindowBuffer) -> dict[str, Any]:
        """Extract DNP3-specific features."""
        messages = buffer.messages
        timestamps = self._get_timestamps(messages)

        # Base features
        features: dict[str, Any] = {
            "protocol": "dnp3",
            "window_size_seconds": key.window_size,
        }

        # Volume features
        features.update(self.compute_volume_features(messages))

        # Timing features
        features.update(self.compute_timing_features(timestamps))

        # DNP3-specific features
        features.update(self._extract_function_code_features(messages))
        features.update(self._extract_address_features(messages))
        features.update(self._extract_object_features(messages))
        features.update(self._extract_control_features(messages))

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
        function_codes = []
        for msg in messages:
            data = msg.get("message", msg)
            # Get application layer function code
            app = data.get("application", {})
            fc = app.get("function_code") or data.get("function_code")
            if fc is not None:
                function_codes.append(fc)

        if not function_codes:
            return {
                "fc_unique_count": 0,
                "fc_read_ratio": 0.0,
                "fc_write_ratio": 0.0,
                "fc_control_ratio": 0.0,
                "fc_response_ratio": 0.0,
                "fc_entropy": 0.0,
            }

        counter = Counter(function_codes)
        total = len(function_codes)

        read_count = sum(counter.get(fc, 0) for fc in self.READ_FUNCTIONS)
        write_count = sum(counter.get(fc, 0) for fc in self.WRITE_FUNCTIONS)
        control_count = sum(counter.get(fc, 0) for fc in self.CONTROL_FUNCTIONS)
        response_count = sum(counter.get(fc, 0) for fc in self.RESPONSE_FUNCTIONS)

        probs = np.array(list(counter.values())) / total
        entropy = float(-np.sum(probs * np.log2(probs + 1e-10)))

        return {
            "fc_unique_count": len(counter),
            "fc_read_ratio": read_count / total,
            "fc_write_ratio": write_count / total,
            "fc_control_ratio": control_count / total,
            "fc_response_ratio": response_count / total,
            "fc_entropy": entropy,
        }

    def _extract_address_features(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract DNP3 address features."""
        sources: list[int] = []
        destinations: list[int] = []

        for msg in messages:
            data = msg.get("message", msg)
            if "source" in data:
                sources.append(data["source"])
            if "destination" in data:
                destinations.append(data["destination"])

        return {
            "dnp3_src_unique": len(set(sources)),
            "dnp3_dst_unique": len(set(destinations)),
            "dnp3_addr_pairs": len(set(zip(sources, destinations, strict=False))) if sources else 0,
        }

    def _extract_object_features(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract DNP3 object group/variation features."""
        groups: list[int] = []
        variations: list[int] = []

        for msg in messages:
            data = msg.get("message", msg)
            app = data.get("application", {})
            objects = app.get("objects", [])

            for obj in objects:
                if "group" in obj:
                    groups.append(obj["group"])
                if "variation" in obj:
                    variations.append(obj["variation"])

        group_counter = Counter(groups)
        total = len(groups)

        # Count common object groups
        binary_input = sum(group_counter.get(g, 0) for g in [1, 2])  # Groups 1, 2
        binary_output = sum(group_counter.get(g, 0) for g in [10, 12])  # Groups 10, 12
        analog_input = sum(group_counter.get(g, 0) for g in [30, 32])  # Groups 30, 32
        analog_output = sum(group_counter.get(g, 0) for g in [40, 41])  # Groups 40, 41

        return {
            "obj_group_unique": len(group_counter),
            "obj_binary_input_ratio": binary_input / total if total > 0 else 0.0,
            "obj_binary_output_ratio": binary_output / total if total > 0 else 0.0,
            "obj_analog_input_ratio": analog_input / total if total > 0 else 0.0,
            "obj_analog_output_ratio": analog_output / total if total > 0 else 0.0,
        }

    def _extract_control_features(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract master/outstation and control features."""
        master_count = 0
        outstation_count = 0
        unsolicited_count = 0

        for msg in messages:
            data = msg.get("message", msg)
            if data.get("is_master"):
                master_count += 1
            else:
                outstation_count += 1

            app = data.get("application", {})
            control = app.get("control", {})
            if control.get("unsolicited"):
                unsolicited_count += 1

        total = master_count + outstation_count

        return {
            "master_ratio": master_count / total if total > 0 else 0.5,
            "unsolicited_count": unsolicited_count,
            "unsolicited_ratio": unsolicited_count / len(messages) if messages else 0.0,
        }
