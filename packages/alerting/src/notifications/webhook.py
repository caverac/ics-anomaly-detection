"""Generic webhook notification channel."""

import httpx
import structlog

from src.config import WebhookSettings
from src.notifications.base import NotificationChannel
from src.schemas.alert import Alert
from src.schemas.incident import Incident

logger = structlog.get_logger()


class WebhookNotifier(NotificationChannel):
    """Generic webhook notification channel."""

    def __init__(self, settings: WebhookSettings) -> None:
        """Initialize the webhook notifier."""
        self.settings = settings
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        """Return the channel name."""
        return "webhook"

    @property
    def enabled(self) -> bool:
        """Return whether the channel is enabled."""
        return self.settings.enabled and bool(self.settings.url)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=self.settings.timeout_seconds,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def send_alert(self, alert: Alert, incident: Incident) -> bool:
        """Send alert via webhook."""
        payload = {
            "type": "alert",
            "alert": alert.to_kafka_message(),
            "incident": {
                "id": incident.id,
                "priority": incident.priority.value,
                "anomaly_count": incident.anomaly_count,
                "status": incident.status.value,
            },
        }

        return await self._send_webhook(payload)

    async def send_escalation(self, incident: Incident, old_priority: str) -> bool:
        """Send escalation via webhook."""
        payload = {
            "type": "escalation",
            "incident": incident.to_redis(),
            "old_priority": old_priority,
            "new_priority": incident.priority.value,
        }

        return await self._send_webhook(payload)

    async def _send_webhook(self, payload: dict) -> bool:
        """Send payload to webhook URL."""
        try:
            client = await self._get_client()
            response = await client.post(
                self.settings.url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            logger.debug(
                "webhook_sent",
                url=self.settings.url,
                status_code=response.status_code,
            )
            return True

        except httpx.HTTPStatusError as e:
            logger.error(
                "webhook_http_error",
                url=self.settings.url,
                status_code=e.response.status_code,
            )
            return False

        except httpx.RequestError as e:
            logger.error(
                "webhook_request_error",
                url=self.settings.url,
                error=str(e),
            )
            return False
