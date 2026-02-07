"""Tests for window manager."""

from datetime import UTC, datetime

import pytest

from src.config import WindowSettings
from src.windows.manager import WindowBuffer, WindowKey, WindowManager


class TestWindowKey:
    """Tests for WindowKey."""

    def test_window_key_creation(self):
        """Test creating a window key."""
        key = WindowKey(
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            protocol="modbus",
            window_size=60,
            window_start=1000,
        )

        assert key.src_ip == "192.168.1.1"
        assert key.dst_ip == "192.168.1.2"
        assert key.protocol == "modbus"
        assert key.window_size == 60
        assert key.window_start == 1000

    def test_window_key_hashable(self):
        """Test that window keys can be used in sets/dicts."""
        key1 = WindowKey(
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            protocol="modbus",
            window_size=60,
            window_start=1000,
        )
        key2 = WindowKey(
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            protocol="modbus",
            window_size=60,
            window_start=1000,
        )

        assert key1 == key2
        assert hash(key1) == hash(key2)

        key_set = {key1}
        assert key2 in key_set

    def test_window_key_inequality(self):
        """Test that different keys are not equal."""
        key1 = WindowKey(
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            protocol="modbus",
            window_size=60,
            window_start=1000,
        )
        key2 = WindowKey(
            src_ip="192.168.1.3",  # Different IP
            dst_ip="192.168.1.2",
            protocol="modbus",
            window_size=60,
            window_start=1000,
        )

        assert key1 != key2


class TestWindowBuffer:
    """Tests for WindowBuffer."""

    def test_buffer_creation(self):
        """Test creating an empty buffer."""
        buffer = WindowBuffer()

        assert len(buffer.messages) == 0
        assert buffer.message_count == 0
        assert buffer.first_timestamp is None
        assert buffer.last_timestamp is None

    def test_add_message(self):
        """Test adding messages to buffer."""
        buffer = WindowBuffer()
        ts1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        ts2 = datetime(2024, 1, 1, 12, 0, 1, tzinfo=UTC)

        buffer.add({"test": "message1"}, ts1)
        buffer.add({"test": "message2"}, ts2)

        assert buffer.message_count == 2
        assert len(buffer.messages) == 2
        assert buffer.first_timestamp == ts1
        assert buffer.last_timestamp == ts2

    def test_timestamp_tracking(self):
        """Test that first and last timestamps are tracked correctly."""
        buffer = WindowBuffer()
        ts1 = datetime(2024, 1, 1, 12, 0, 5, tzinfo=UTC)
        ts2 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)  # Earlier
        ts3 = datetime(2024, 1, 1, 12, 0, 10, tzinfo=UTC)

        buffer.add({"test": "1"}, ts1)
        buffer.add({"test": "2"}, ts2)  # Should become first
        buffer.add({"test": "3"}, ts3)  # Should become last

        assert buffer.first_timestamp == ts2
        assert buffer.last_timestamp == ts3


class TestWindowManager:
    """Tests for WindowManager."""

    @pytest.fixture
    def settings(self):
        """Create test window settings."""
        return WindowSettings(window_sizes=[60, 300])

    def test_manager_creation(self, settings):
        """Test creating a window manager."""
        manager = WindowManager(settings=settings)

        assert manager.settings.window_sizes == [60, 300]
        assert len(manager._windows) == 0

    def test_add_message_creates_windows(self, settings):
        """Test that adding a message creates windows for each size."""
        manager = WindowManager(settings=settings)

        message = {
            "timestamp": "2024-01-01T12:00:00Z",
            "src_ip": "192.168.1.1",
            "dst_ip": "192.168.1.2",
            "protocol": "modbus",
        }

        manager.add_message(message)

        # Should create 2 windows (one for each window size)
        assert len(manager._windows) == 2

    def test_add_multiple_messages_same_window(self, settings):
        """Test that messages in same window are grouped."""
        settings = WindowSettings(window_sizes=[60])
        manager = WindowManager(settings=settings)

        # Two messages within the same 60-second window
        manager.add_message({
            "timestamp": "2024-01-01T12:00:00Z",
            "src_ip": "192.168.1.1",
            "dst_ip": "192.168.1.2",
            "protocol": "modbus",
        })
        manager.add_message({
            "timestamp": "2024-01-01T12:00:30Z",
            "src_ip": "192.168.1.1",
            "dst_ip": "192.168.1.2",
            "protocol": "modbus",
        })

        assert len(manager._windows) == 1
        key = list(manager._windows.keys())[0]
        assert manager._windows[key].message_count == 2

    def test_different_flows_separate_windows(self):
        """Test that different src/dst pairs get separate windows."""
        settings = WindowSettings(window_sizes=[60])
        manager = WindowManager(settings=settings)

        manager.add_message({
            "timestamp": "2024-01-01T12:00:00Z",
            "src_ip": "192.168.1.1",
            "dst_ip": "192.168.1.2",
            "protocol": "modbus",
        })
        manager.add_message({
            "timestamp": "2024-01-01T12:00:00Z",
            "src_ip": "192.168.1.3",
            "dst_ip": "192.168.1.4",
            "protocol": "modbus",
        })

        assert len(manager._windows) == 2

    def test_different_protocols_separate_windows(self):
        """Test that different protocols get separate windows."""
        settings = WindowSettings(window_sizes=[60])
        manager = WindowManager(settings=settings)

        manager.add_message({
            "timestamp": "2024-01-01T12:00:00Z",
            "src_ip": "192.168.1.1",
            "dst_ip": "192.168.1.2",
            "protocol": "modbus",
        })
        manager.add_message({
            "timestamp": "2024-01-01T12:00:00Z",
            "src_ip": "192.168.1.1",
            "dst_ip": "192.168.1.2",
            "protocol": "dnp3",
        })

        assert len(manager._windows) == 2

    def test_get_closed_windows(self):
        """Test getting closed windows."""
        settings = WindowSettings(window_sizes=[60])
        manager = WindowManager(settings=settings)

        # Add message at 12:00:00
        manager.add_message({
            "timestamp": "2024-01-01T12:00:00Z",
            "src_ip": "192.168.1.1",
            "dst_ip": "192.168.1.2",
            "protocol": "modbus",
        })

        # Check at 12:00:30 - window not closed yet
        check_time = datetime(2024, 1, 1, 12, 0, 30, tzinfo=UTC)
        closed = manager.get_closed_windows(check_time)
        assert len(closed) == 0

        # Check at 12:01:01 - window should be closed
        check_time = datetime(2024, 1, 1, 12, 1, 1, tzinfo=UTC)
        closed = manager.get_closed_windows(check_time)
        assert len(closed) == 1

        # Window should be removed after getting closed
        assert len(manager._windows) == 0

    def test_get_closed_windows_returns_buffer(self):
        """Test that closed windows return both key and buffer."""
        settings = WindowSettings(window_sizes=[60])
        manager = WindowManager(settings=settings)

        manager.add_message({
            "timestamp": "2024-01-01T12:00:00Z",
            "src_ip": "192.168.1.1",
            "dst_ip": "192.168.1.2",
            "protocol": "modbus",
            "payload": "test",
        })

        check_time = datetime(2024, 1, 1, 12, 1, 1, tzinfo=UTC)
        closed = manager.get_closed_windows(check_time)

        key, buffer = closed[0]
        assert key.protocol == "modbus"
        assert buffer.message_count == 1
        assert buffer.messages[0]["payload"] == "test"

    def test_get_window_start(self):
        """Test window start time computation."""
        settings = WindowSettings(window_sizes=[60])
        manager = WindowManager(settings=settings)

        # Timestamp at 12:00:30 should have window start at 12:00:00 for 60s window
        timestamp = datetime(2024, 1, 1, 12, 0, 30, tzinfo=UTC)
        window_start = manager._get_window_start(timestamp, 60)

        # 2024-01-01 12:00:00 UTC = 1704110400
        assert window_start == 1704110400

    def test_parse_timestamp_z_suffix(self):
        """Test timestamp parsing with Z suffix."""
        settings = WindowSettings(window_sizes=[60])
        manager = WindowManager(settings=settings)

        ts = manager._parse_timestamp("2024-01-01T12:00:00Z")
        assert ts.year == 2024
        assert ts.month == 1
        assert ts.day == 1
        assert ts.hour == 12

    def test_parse_timestamp_offset(self):
        """Test timestamp parsing with offset."""
        settings = WindowSettings(window_sizes=[60])
        manager = WindowManager(settings=settings)

        ts = manager._parse_timestamp("2024-01-01T12:00:00+00:00")
        assert ts.year == 2024
        assert ts.hour == 12

    def test_get_stats(self):
        """Test getting window manager statistics."""
        settings = WindowSettings(window_sizes=[60, 300])
        manager = WindowManager(settings=settings)

        manager.add_message({
            "timestamp": "2024-01-01T12:00:00Z",
            "src_ip": "192.168.1.1",
            "dst_ip": "192.168.1.2",
            "protocol": "modbus",
        })

        stats = manager.get_stats()

        assert stats["active_windows"] == 2  # One for each window size
        assert stats["total_buffered_messages"] == 2  # Same message in both windows
        assert stats["window_sizes"] == [60, 300]

    def test_missing_timestamp_uses_current_time(self):
        """Test handling messages without timestamp."""
        settings = WindowSettings(window_sizes=[60])
        manager = WindowManager(settings=settings)

        # Message without timestamp should still be added
        manager.add_message({
            "src_ip": "192.168.1.1",
            "dst_ip": "192.168.1.2",
            "protocol": "modbus",
        })

        assert len(manager._windows) == 1

    def test_default_values_for_missing_fields(self):
        """Test default values when fields are missing."""
        settings = WindowSettings(window_sizes=[60])
        manager = WindowManager(settings=settings)

        manager.add_message({
            "timestamp": "2024-01-01T12:00:00Z",
        })

        key = list(manager._windows.keys())[0]
        assert key.src_ip == "unknown"
        assert key.dst_ip == "unknown"
        assert key.protocol == "unknown"
