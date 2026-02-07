"""Slack notification channel."""

import httpx
import structlog

from src.config import SlackSettings
from src.notifications.base import NotificationChannel
from src.schemas.alert import Alert, AlertSeverity
from src.schemas.incident import Incident, IncidentPriority

logger = structlog.get_logger()


class SlackNotifier(NotificationChannel):
    """Slack webhook notification channel."""

    # Severity to color mapping
    SEVERITY_COLORS = {
        AlertSeverity.LOW: "#36a64f",      # Green
        AlertSeverity.MEDIUM: "#f2c744",   # Yellow
        AlertSeverity.HIGH: "#ff9900",     # Orange
        AlertSeverity.CRITICAL: "#ff0000", # Red
    }

    # Priority to color mapping
    PRIORITY_COLORS = {
        IncidentPriority.P4: "#36a64f",    # Green
        IncidentPriority.P3: "#f2c744",    # Yellow
        IncidentPriority.P2: "#ff9900",    # Orange
        IncidentPriority.P1: "#ff0000",    # Red
    }

    def __init__(self, settings: SlackSettings) -> None:
        """Initialize the Slack notifier."""
        self.settings = settings
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        """Return the channel name."""
        return "slack"

    @property
    def enabled(self) -> bool:
        """Return whether the channel is enabled."""
        return self.settings.enabled and bool(self.settings.webhook_url)

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
        """Send alert via Slack."""
        color = self.SEVERITY_COLORS.get(alert.severity, "#808080")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"ICS Alert: {alert.title}",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Severity:*\n{alert.severity.value.upper()}"},
                    {"type": "mrkdwn", "text": f"*Score:*\n{alert.ensemble_score:.3f}"},
                    {"type": "mrkdwn", "text": f"*Source:*\n{alert.source.src_ip}"},
                    {"type": "mrkdwn", "text": f"*Destination:*\n{alert.source.dst_ip}"},
                    {"type": "mrkdwn", "text": f"*Protocol:*\n{alert.source.protocol.upper()}"},
                    {"type": "mrkdwn", "text": f"*Type:*\n{alert.anomaly_type or 'Unknown'}"},
                ]
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Incident: {incident.id[:8]}... | Priority: {incident.priority.value} | Anomalies: {incident.anomaly_count}"}
                ]
            }
        ]

        payload = {
            "channel": self.settings.channel,
            "attachments": [{"color": color, "blocks": blocks}],
        }

        return await self._send_slack(payload)

    async def send_escalation(self, incident: Incident, old_priority: str) -> bool:
        """Send escalation via Slack."""
        color = self.PRIORITY_COLORS.get(incident.priority, "#808080")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Incident Escalated: {incident.title}",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Priority Change:*\n{old_priority} → {incident.priority.value}"},
                    {"type": "mrkdwn", "text": f"*Anomaly Count:*\n{incident.anomaly_count}"},
                    {"type": "mrkdwn", "text": f"*Max Score:*\n{incident.max_ensemble_score:.3f}"},
                    {"type": "mrkdwn", "text": f"*Sources:*\n{', '.join(incident.src_ips[:3])}"},
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Targets:* {', '.join(incident.dst_ips[:5])}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Incident ID: {incident.id}"}
                ]
            }
        ]

        payload = {
            "channel": self.settings.channel,
            "attachments": [{"color": color, "blocks": blocks}],
        }

        return await self._send_slack(payload)

    async def _send_slack(self, payload: dict) -> bool:
        """Send payload to Slack webhook."""
        try:
            client = await self._get_client()
            response = await client.post(
                self.settings.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            logger.debug("slack_message_sent")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(
                "slack_http_error",
                status_code=e.response.status_code,
            )
            return False

        except httpx.RequestError as e:
            logger.error(
                "slack_request_error",
                error=str(e),
            )
            return False
