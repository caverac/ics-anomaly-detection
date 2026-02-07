"""Tests for feature extractors."""

from datetime import UTC, datetime

import pytest

from src.extractors.base import extract_features
from src.extractors.dnp3 import DNP3Extractor
from src.extractors.modbus import ModbusExtractor
from src.extractors.opcua import OPCUAExtractor
from src.windows.manager import WindowBuffer, WindowKey


def add_messages_to_buffer(buffer: WindowBuffer, messages: list[dict]) -> None:
    """Helper to add messages to a buffer with timestamps."""
    for msg in messages:
        ts_str = msg.get("timestamp", "")
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")) if ts_str else datetime.now(UTC)
        buffer.add(msg, ts)


@pytest.fixture
def window_key() -> WindowKey:
    """Create a test window key."""
    return WindowKey(
        src_ip="192.168.1.1",
        dst_ip="192.168.1.2",
        protocol="modbus",
        window_size=60,
        window_start=1000,
    )


@pytest.fixture
def modbus_messages() -> list[dict]:
    """Create test Modbus messages."""
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    return [
        {
            "timestamp": base_time.isoformat(),
            "payload_size": 100,
            "function_code": 3,
            "unit_id": 1,
            "message": {
                "function_code": 3,
                "unit_id": 1,
                "start_address": 0,
                "quantity": 10,
            },
        },
        {
            "timestamp": (base_time.replace(second=1)).isoformat(),
            "payload_size": 50,
            "function_code": 3,
            "unit_id": 1,
            "message": {
                "function_code": 3,
                "unit_id": 1,
                "start_address": 10,
                "quantity": 5,
            },
        },
        {
            "timestamp": (base_time.replace(second=2)).isoformat(),
            "payload_size": 75,
            "function_code": 6,
            "unit_id": 2,
            "message": {
                "function_code": 6,
                "unit_id": 2,
                "start_address": 100,
                "quantity": 1,
            },
        },
    ]


@pytest.fixture
def dnp3_messages() -> list[dict]:
    """Create test DNP3 messages."""
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    return [
        {
            "timestamp": base_time.isoformat(),
            "payload_size": 120,
            "message": {
                "source": 1,
                "destination": 10,
                "is_master": True,
                "application": {
                    "function_code": 0x01,
                    "objects": [{"group": 1, "variation": 2}],
                    "control": {"unsolicited": False},
                },
            },
        },
        {
            "timestamp": (base_time.replace(second=1)).isoformat(),
            "payload_size": 200,
            "message": {
                "source": 10,
                "destination": 1,
                "is_master": False,
                "application": {
                    "function_code": 0x81,
                    "objects": [{"group": 30, "variation": 1}],
                    "control": {"unsolicited": False},
                },
            },
        },
    ]


@pytest.fixture
def opcua_messages() -> list[dict]:
    """Create test OPC-UA messages."""
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    return [
        {
            "timestamp": base_time.isoformat(),
            "payload_size": 256,
            "message": {
                "message_type": "Hello",
                "secure_channel_id": 1,
                "security_token_id": 100,
                "service_type": "OpenSecureChannel",
                "sequence_number": 1,
            },
        },
        {
            "timestamp": (base_time.replace(second=1)).isoformat(),
            "payload_size": 128,
            "message": {
                "message_type": "Acknowledge",
                "secure_channel_id": 1,
                "security_token_id": 100,
                "service_type": "OpenSecureChannel",
                "sequence_number": 2,
            },
        },
        {
            "timestamp": (base_time.replace(second=2)).isoformat(),
            "payload_size": 512,
            "message": {
                "message_type": "Message",
                "secure_channel_id": 1,
                "security_token_id": 100,
                "service_type": "Read",
                "sequence_number": 3,
            },
        },
    ]


class TestBaseExtractor:
    """Tests for BaseExtractor methods."""

    def test_compute_timing_features_empty(self):
        """Test timing features with no timestamps."""
        extractor = ModbusExtractor()
        features = extractor.compute_timing_features([])

        assert features["iat_mean"] == 0.0
        assert features["iat_std"] == 0.0
        assert features["iat_min"] == 0.0
        assert features["iat_max"] == 0.0
        assert features["iat_median"] == 0.0

    def test_compute_timing_features_single(self):
        """Test timing features with single timestamp."""
        extractor = ModbusExtractor()
        timestamps = [datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)]
        features = extractor.compute_timing_features(timestamps)

        assert features["iat_mean"] == 0.0

    def test_compute_timing_features_multiple(self):
        """Test timing features with multiple timestamps."""
        extractor = ModbusExtractor()
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        timestamps = [
            base_time,
            base_time.replace(second=1),
            base_time.replace(second=2),
        ]
        features = extractor.compute_timing_features(timestamps)

        assert features["iat_mean"] == 1.0
        assert features["iat_std"] == 0.0
        assert features["iat_min"] == 1.0
        assert features["iat_max"] == 1.0

    def test_compute_volume_features_empty(self):
        """Test volume features with no messages."""
        extractor = ModbusExtractor()
        features = extractor.compute_volume_features([])

        assert features["message_count"] == 0
        assert features["bytes_total"] == 0

    def test_compute_volume_features(self, modbus_messages):
        """Test volume features computation."""
        extractor = ModbusExtractor()
        features = extractor.compute_volume_features(modbus_messages)

        assert features["message_count"] == 3
        assert features["bytes_total"] == 225  # 100 + 50 + 75
        assert features["bytes_mean"] == 75.0
        assert features["bytes_min"] == 50
        assert features["bytes_max"] == 100


class TestModbusExtractor:
    """Tests for ModbusExtractor."""

    def test_extract_function_code_features(self, modbus_messages, window_key):
        """Test function code feature extraction."""
        extractor = ModbusExtractor()
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, modbus_messages)

        features = extractor.extract(window_key, buffer)

        assert features["fc_unique_count"] == 2  # FC 3 and 6
        assert features["fc_read_ratio"] == pytest.approx(2 / 3)  # 2 reads out of 3
        assert features["fc_write_ratio"] == pytest.approx(1 / 3)  # 1 write out of 3

    def test_extract_unit_id_features(self, modbus_messages, window_key):
        """Test unit ID feature extraction."""
        extractor = ModbusExtractor()
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, modbus_messages)

        features = extractor.extract(window_key, buffer)

        assert features["unit_id_unique_count"] == 2  # Unit IDs 1 and 2

    def test_extract_address_features(self, modbus_messages, window_key):
        """Test address feature extraction."""
        extractor = ModbusExtractor()
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, modbus_messages)

        features = extractor.extract(window_key, buffer)

        assert features["addr_unique_count"] == 3  # Addresses 0, 10, 100
        assert features["addr_min"] == 0
        assert features["addr_max"] == 100
        assert features["addr_range"] == 100

    def test_extract_exception_features_no_exceptions(self, modbus_messages, window_key):
        """Test exception features with no exceptions."""
        extractor = ModbusExtractor()
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, modbus_messages)

        features = extractor.extract(window_key, buffer)

        assert features["exception_count"] == 0
        assert features["exception_ratio"] == 0.0

    def test_extract_with_exceptions(self, window_key):
        """Test extraction with exception responses."""
        extractor = ModbusExtractor()
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, [{
            "timestamp": "2024-01-01T12:00:00Z",
            "payload_size": 50,
            "message": {
                "function_code": 3,
                "is_exception": True,
                "exception_code": 2,
            },
        }])

        features = extractor.extract(window_key, buffer)

        assert features["exception_count"] == 1
        assert features["exception_ratio"] == 1.0
        assert features["exception_codes_unique"] == 1


class TestDNP3Extractor:
    """Tests for DNP3Extractor."""

    def test_extract_function_code_features(self, dnp3_messages):
        """Test DNP3 function code extraction."""
        extractor = DNP3Extractor()
        key = WindowKey(
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            protocol="dnp3",
            window_size=60,
            window_start=1000,
        )
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, dnp3_messages)

        features = extractor.extract(key, buffer)

        assert features["fc_unique_count"] == 2
        assert features["fc_read_ratio"] == 0.5  # 1 read out of 2
        assert features["fc_response_ratio"] == 0.5  # 1 response out of 2

    def test_extract_address_features(self, dnp3_messages):
        """Test DNP3 address extraction."""
        extractor = DNP3Extractor()
        key = WindowKey(
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            protocol="dnp3",
            window_size=60,
            window_start=1000,
        )
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, dnp3_messages)

        features = extractor.extract(key, buffer)

        assert features["dnp3_src_unique"] == 2  # Sources 1 and 10
        assert features["dnp3_dst_unique"] == 2  # Destinations 10 and 1
        assert features["dnp3_addr_pairs"] == 2

    def test_extract_object_features(self, dnp3_messages):
        """Test DNP3 object extraction."""
        extractor = DNP3Extractor()
        key = WindowKey(
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            protocol="dnp3",
            window_size=60,
            window_start=1000,
        )
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, dnp3_messages)

        features = extractor.extract(key, buffer)

        assert features["obj_group_unique"] == 2  # Groups 1 and 30

    def test_extract_control_features(self, dnp3_messages):
        """Test DNP3 control features."""
        extractor = DNP3Extractor()
        key = WindowKey(
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            protocol="dnp3",
            window_size=60,
            window_start=1000,
        )
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, dnp3_messages)

        features = extractor.extract(key, buffer)

        assert features["master_ratio"] == 0.5  # 1 master out of 2
        assert features["unsolicited_count"] == 0


class TestOPCUAExtractor:
    """Tests for OPCUAExtractor."""

    def test_extract_message_type_features(self, opcua_messages):
        """Test OPC-UA message type extraction."""
        extractor = OPCUAExtractor()
        key = WindowKey(
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            protocol="opcua",
            window_size=60,
            window_start=1000,
        )
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, opcua_messages)

        features = extractor.extract(key, buffer)

        assert features["msg_type_unique"] == 3  # Hello, Acknowledge, Message
        assert features["msg_handshake_ratio"] == pytest.approx(2 / 3)  # Hello + Acknowledge
        assert features["msg_data_ratio"] == pytest.approx(1 / 3)  # Message

    def test_extract_channel_features(self, opcua_messages):
        """Test OPC-UA channel extraction."""
        extractor = OPCUAExtractor()
        key = WindowKey(
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            protocol="opcua",
            window_size=60,
            window_start=1000,
        )
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, opcua_messages)

        features = extractor.extract(key, buffer)

        assert features["channel_unique"] == 1
        assert features["token_unique"] == 1
        assert features["channel_reuse_ratio"] == pytest.approx(2 / 3)  # 3 messages, 1 channel

    def test_extract_service_features(self, opcua_messages):
        """Test OPC-UA service extraction."""
        extractor = OPCUAExtractor()
        key = WindowKey(
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            protocol="opcua",
            window_size=60,
            window_start=1000,
        )
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, opcua_messages)

        features = extractor.extract(key, buffer)

        assert features["service_unique"] == 2  # OpenSecureChannel and Read
        assert features["service_open_channel"] == 2
        assert features["sequence_gaps"] == 0  # Sequential: 1, 2, 3


class TestExtractFeatures:
    """Tests for the extract_features function."""

    def test_extract_features_modbus(self, modbus_messages, window_key):
        """Test feature extraction with modbus protocol."""
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, modbus_messages)

        features = extract_features(window_key, buffer)

        assert features["protocol"] == "modbus"
        assert "_window_key" in features
        assert "_extracted_at" in features

    def test_extract_features_dnp3(self, dnp3_messages):
        """Test feature extraction with DNP3 protocol."""
        key = WindowKey(
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            protocol="dnp3",
            window_size=60,
            window_start=1000,
        )
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, dnp3_messages)

        features = extract_features(key, buffer)

        assert features["protocol"] == "dnp3"

    def test_extract_features_opcua(self, opcua_messages):
        """Test feature extraction with OPC-UA protocol."""
        key = WindowKey(
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            protocol="opcua",
            window_size=60,
            window_start=1000,
        )
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, opcua_messages)

        features = extract_features(key, buffer)

        assert features["protocol"] == "opcua"

    def test_extract_features_unknown_protocol(self, modbus_messages):
        """Test feature extraction with unknown protocol falls back to modbus."""
        key = WindowKey(
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            protocol="unknown",
            window_size=60,
            window_start=1000,
        )
        buffer = WindowBuffer()
        add_messages_to_buffer(buffer, modbus_messages)

        features = extract_features(key, buffer)

        # Should still extract features using modbus extractor as fallback
        assert "fc_unique_count" in features
