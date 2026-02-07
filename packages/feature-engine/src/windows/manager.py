"""Window manager for time-based feature aggregation."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog

from src.config import WindowSettings

logger = structlog.get_logger()


@dataclass
class WindowKey:
    """Unique key for a window."""

    src_ip: str
    dst_ip: str
    protocol: str
    window_size: int  # seconds
    window_start: int  # Unix timestamp (floored to window boundary)

    def __hash__(self) -> int:
        return hash((self.src_ip, self.dst_ip, self.protocol, self.window_size, self.window_start))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WindowKey):
            return False
        return (
            self.src_ip == other.src_ip
            and self.dst_ip == other.dst_ip
            and self.protocol == other.protocol
            and self.window_size == other.window_size
            and self.window_start == other.window_start
        )


@dataclass
class WindowBuffer:
    """Buffer for messages in a window."""

    messages: list[dict[str, Any]] = field(default_factory=list)
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None
    message_count: int = 0

    def add(self, message: dict[str, Any], timestamp: datetime) -> None:
        """Add a message to the buffer."""
        self.messages.append(message)
        self.message_count += 1

        if self.first_timestamp is None or timestamp < self.first_timestamp:
            self.first_timestamp = timestamp
        if self.last_timestamp is None or timestamp > self.last_timestamp:
            self.last_timestamp = timestamp


class WindowManager:
    """Manages time windows for feature aggregation."""

    def __init__(self, settings: WindowSettings) -> None:
        """Initialize the window manager."""
        self.settings = settings
        self._windows: dict[WindowKey, WindowBuffer] = defaultdict(WindowBuffer)
        self._last_emit_time: int = 0

    def _get_window_start(self, timestamp: datetime, window_size: int) -> int:
        """Get the window start time for a given timestamp."""
        ts = int(timestamp.timestamp())
        return ts - (ts % window_size)

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse an ISO 8601 timestamp string."""
        # Handle various ISO 8601 formats
        ts = timestamp_str.replace("Z", "+00:00")
        return datetime.fromisoformat(ts)

    def add_message(self, message: dict[str, Any]) -> None:
        """Add a message to the appropriate windows."""
        # Extract message fields
        src_ip = message.get("src_ip", "unknown")
        dst_ip = message.get("dst_ip", "unknown")
        protocol = message.get("protocol", message.get("ics_protocol", "unknown"))
        timestamp_str = message.get("timestamp", "")

        if not timestamp_str:
            timestamp = datetime.now()
        else:
            try:
                timestamp = self._parse_timestamp(timestamp_str)
            except ValueError:
                timestamp = datetime.now()

        # Add to each window size
        for window_size in self.settings.window_sizes:
            window_start = self._get_window_start(timestamp, window_size)
            key = WindowKey(
                src_ip=src_ip,
                dst_ip=dst_ip,
                protocol=protocol,
                window_size=window_size,
                window_start=window_start,
            )
            self._windows[key].add(message, timestamp)

    def get_closed_windows(self, current_time: datetime | None = None) -> list[tuple[WindowKey, WindowBuffer]]:
        """Get windows that are ready to be closed and processed.

        Returns windows where current_time > window_start + window_size.
        """
        if current_time is None:
            current_time = datetime.now()

        current_ts = int(current_time.timestamp())
        closed: list[tuple[WindowKey, WindowBuffer]] = []

        keys_to_remove = []
        for key, buffer in self._windows.items():
            window_end = key.window_start + key.window_size
            if current_ts >= window_end:
                closed.append((key, buffer))
                keys_to_remove.append(key)

        # Remove closed windows
        for key in keys_to_remove:
            del self._windows[key]

        if closed:
            logger.debug("windows_closed", count=len(closed))

        return closed

    def get_stats(self) -> dict[str, Any]:
        """Get current window manager statistics."""
        total_messages = sum(buf.message_count for buf in self._windows.values())
        return {
            "active_windows": len(self._windows),
            "total_buffered_messages": total_messages,
            "window_sizes": self.settings.window_sizes,
        }
