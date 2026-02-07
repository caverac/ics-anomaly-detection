"""Base notification channel and manager."""

from abc import ABC, abstractmethod

import structlog

from src.schemas.alert import Alert
from src.schemas.incident import Incident

logger = structlog.get_logger()


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the channel name."""
        pass

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Return whether the channel is enabled."""
        pass

    @abstractmethod
    async def send_alert(self, alert: Alert, incident: Incident) -> bool:
        """Send an alert notification.

        Args:
            alert: The alert to send.
            incident: The parent incident.

        Returns:
            True if the notification was sent successfully.
        """
        pass

    @abstractmethod
    async def send_escalation(self, incident: Incident, old_priority: str) -> bool:
        """Send an escalation notification.

        Args:
            incident: The escalated incident.
            old_priority: The previous priority level.

        Returns:
            True if the notification was sent successfully.
        """
        pass


class NotificationManager:
    """Manages multiple notification channels."""

    def __init__(self) -> None:
        """Initialize the notification manager."""
        self._channels: list[NotificationChannel] = []
        self._sent_count = 0
        self._error_count = 0

    def add_channel(self, channel: NotificationChannel) -> None:
        """Add a notification channel."""
        if channel.enabled:
            self._channels.append(channel)
            logger.info("notification_channel_added", channel=channel.name)

    async def notify_alert(self, alert: Alert, incident: Incident) -> None:
        """Send alert notifications to all enabled channels."""
        for channel in self._channels:
            try:
                success = await channel.send_alert(alert, incident)
                if success:
                    self._sent_count += 1
                else:
                    self._error_count += 1
            except Exception as e:
                self._error_count += 1
                logger.error(
                    "notification_error",
                    channel=channel.name,
                    error=str(e),
                )

    async def notify_escalation(self, incident: Incident, old_priority: str) -> None:
        """Send escalation notifications to all enabled channels."""
        for channel in self._channels:
            try:
                success = await channel.send_escalation(incident, old_priority)
                if success:
                    self._sent_count += 1
                else:
                    self._error_count += 1
            except Exception as e:
                self._error_count += 1
                logger.error(
                    "escalation_notification_error",
                    channel=channel.name,
                    error=str(e),
                )

    def get_stats(self) -> dict[str, int]:
        """Get notification statistics."""
        return {
            "channels": len(self._channels),
            "sent": self._sent_count,
            "errors": self._error_count,
        }
