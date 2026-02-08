"""Splunk HEC (HTTP Event Collector) notification channel."""

import time

import httpx
import structlog

from src.config import SplunkSettings
from src.notifications.base import NotificationChannel
from src.schemas.alert import Alert
from src.schemas.incident import Incident

logger = structlog.get_logger()


class SplunkNotifier(NotificationChannel):
    """Splunk HTTP Event Collector notification channel."""

    def __init__(self, settings: SplunkSettings) -> None:
        """Initialize the Splunk HEC notifier."""
        self.settings = settings
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        """Return the channel name."""
        return "splunk"

    @property
    def enabled(self) -> bool:
        """Return whether the channel is enabled."""
        return self.settings.enabled and bool(self.settings.hec_url) and bool(self.settings.hec_token)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=self.settings.timeout_seconds,
                verify=self.settings.verify_ssl,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_event(self, event_data: dict, event_type: str) -> dict:
        """Build a Splunk HEC event payload."""
        return {
            "time": time.time(),
            "host": "ics-alerting",
            "source": self.settings.source,
            "sourcetype": self.settings.sourcetype,
            "index": self.settings.index,
            "event": {
                "event_type": event_type,
                **event_data,
            },
        }

    async def send_alert(self, alert: Alert, incident: Incident) -> bool:
        """Send alert to Splunk HEC."""
        event_data = {
            "alert_id": alert.id,
            "incident_id": incident.id,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "title": alert.title,
            "description": alert.description,
            "src_ip": alert.source.src_ip,
            "dst_ip": alert.source.dst_ip,
            "protocol": alert.source.protocol,
            "anomaly_type": alert.anomaly_type,
            "ensemble_score": alert.ensemble_score,
            "confidence": alert.confidence,
            "incident_priority": incident.priority.value,
            "incident_anomaly_count": incident.anomaly_count,
        }

        payload = self._build_event(event_data, "ics_alert")
        return await self._send_to_hec(payload)

    async def send_escalation(self, incident: Incident, old_priority: str) -> bool:
        """Send escalation to Splunk HEC."""
        event_data = {
            "incident_id": incident.id,
            "old_priority": old_priority,
            "new_priority": incident.priority.value,
            "anomaly_count": incident.anomaly_count,
            "src_ips": list(incident.src_ips),
            "dst_ips": list(incident.dst_ips),
            "anomaly_types": list(incident.anomaly_types),
            "title": incident.title,
            "description": incident.description,
        }

        payload = self._build_event(event_data, "ics_escalation")
        return await self._send_to_hec(payload)

    async def _send_to_hec(self, payload: dict) -> bool:
        """Send payload to Splunk HEC endpoint."""
        try:
            client = await self._get_client()
            response = await client.post(
                self.settings.hec_url,
                json=payload,
                headers={
                    "Authorization": f"Splunk {self.settings.hec_token}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()

            logger.debug(
                "splunk_hec_sent",
                url=self.settings.hec_url,
                status_code=response.status_code,
            )
            return True

        except httpx.HTTPStatusError as e:
            logger.error(
                "splunk_hec_http_error",
                url=self.settings.hec_url,
                status_code=e.response.status_code,
                response_text=e.response.text[:200],
            )
            return False

        except httpx.RequestError as e:
            logger.error(
                "splunk_hec_request_error",
                url=self.settings.hec_url,
                error=str(e),
            )
            return False
