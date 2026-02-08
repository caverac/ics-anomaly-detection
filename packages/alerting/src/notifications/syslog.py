"""Syslog notification channel with CEF (Common Event Format) support."""

import asyncio
import socket
from datetime import datetime, timezone
from enum import IntEnum

import structlog

from src.config import SyslogSettings
from src.notifications.base import NotificationChannel
from src.schemas.alert import Alert, AlertSeverity
from src.schemas.incident import Incident, IncidentPriority

logger = structlog.get_logger()


class SyslogFacility(IntEnum):
    """Syslog facility codes."""

    LOCAL0 = 16
    LOCAL1 = 17
    LOCAL2 = 18
    LOCAL3 = 19
    LOCAL4 = 20
    LOCAL5 = 21
    LOCAL6 = 22
    LOCAL7 = 23


class SyslogSeverity(IntEnum):
    """Syslog severity codes."""

    EMERGENCY = 0
    ALERT = 1
    CRITICAL = 2
    ERROR = 3
    WARNING = 4
    NOTICE = 5
    INFO = 6
    DEBUG = 7


class SyslogNotifier(NotificationChannel):
    """Syslog notification channel with CEF format support."""

    # CEF severity mapping (0-10 scale)
    ALERT_SEVERITY_MAP = {
        AlertSeverity.CRITICAL: 10,
        AlertSeverity.HIGH: 7,
        AlertSeverity.MEDIUM: 5,
        AlertSeverity.LOW: 3,
    }

    PRIORITY_SEVERITY_MAP = {
        IncidentPriority.P1: 10,
        IncidentPriority.P2: 7,
        IncidentPriority.P3: 5,
        IncidentPriority.P4: 3,
    }

    def __init__(self, settings: SyslogSettings) -> None:
        """Initialize the syslog notifier."""
        self.settings = settings
        self._socket: socket.socket | None = None
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        """Return the channel name."""
        return "syslog"

    @property
    def enabled(self) -> bool:
        """Return whether the channel is enabled."""
        return self.settings.enabled and bool(self.settings.host)

    def _get_socket(self) -> socket.socket:
        """Get or create the socket."""
        if not self._socket:
            if self.settings.protocol.lower() == "tcp":
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.settimeout(self.settings.timeout_seconds)
                self._socket.connect((self.settings.host, self.settings.port))
            else:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._socket.settimeout(self.settings.timeout_seconds)
        return self._socket

    def close(self) -> None:
        """Close the socket."""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    def _calculate_priority(self, severity: SyslogSeverity) -> int:
        """Calculate syslog priority value."""
        facility = SyslogFacility[self.settings.facility.upper()]
        return (facility * 8) + severity

    def _escape_cef_value(self, value: str) -> str:
        """Escape special characters in CEF extension values."""
        return value.replace("\\", "\\\\").replace("=", "\\=").replace("\n", "\\n")

    def _build_cef_message(
        self,
        signature_id: str,
        name: str,
        severity: int,
        extensions: dict[str, str],
    ) -> str:
        """Build a CEF formatted message.

        CEF format:
        CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension
        """
        # Build extension string
        ext_parts = []
        for key, value in extensions.items():
            if value is not None:
                ext_parts.append(f"{key}={self._escape_cef_value(str(value))}")
        extension = " ".join(ext_parts)

        return (
            f"CEF:0|ICS-Anomaly-Detection|Alerting|1.0|"
            f"{signature_id}|{name}|{severity}|{extension}"
        )

    def _build_syslog_message(
        self,
        severity: SyslogSeverity,
        cef_message: str,
    ) -> str:
        """Build a complete syslog message with CEF payload."""
        priority = self._calculate_priority(severity)
        timestamp = datetime.now(timezone.utc).strftime("%b %d %H:%M:%S")
        hostname = self.settings.hostname or socket.gethostname()

        # RFC 3164 format: <priority>timestamp hostname tag: message
        return f"<{priority}>{timestamp} {hostname} ics-alerting: {cef_message}"

    async def send_alert(self, alert: Alert, incident: Incident) -> bool:
        """Send alert via syslog in CEF format."""
        cef_severity = self.ALERT_SEVERITY_MAP.get(alert.severity, 5)

        extensions = {
            "src": alert.source.src_ip,
            "dst": alert.source.dst_ip,
            "proto": alert.source.protocol,
            "cs1": alert.id,
            "cs1Label": "AlertID",
            "cs2": incident.id,
            "cs2Label": "IncidentID",
            "cs3": alert.anomaly_type or "unknown",
            "cs3Label": "AnomalyType",
            "cfp1": f"{alert.ensemble_score:.3f}",
            "cfp1Label": "EnsembleScore",
            "cfp2": f"{alert.confidence:.3f}",
            "cfp2Label": "Confidence",
            "msg": alert.title,
        }

        cef_message = self._build_cef_message(
            signature_id=f"ICS-{alert.severity.value.upper()}",
            name=alert.title,
            severity=cef_severity,
            extensions=extensions,
        )

        syslog_severity = self._map_alert_to_syslog_severity(alert.severity)
        syslog_message = self._build_syslog_message(syslog_severity, cef_message)

        return await self._send_syslog(syslog_message)

    async def send_escalation(self, incident: Incident, old_priority: str) -> bool:
        """Send escalation via syslog in CEF format."""
        cef_severity = self.PRIORITY_SEVERITY_MAP.get(incident.priority, 5)

        extensions = {
            "cs1": incident.id,
            "cs1Label": "IncidentID",
            "cs2": old_priority,
            "cs2Label": "OldPriority",
            "cs3": incident.priority.value,
            "cs3Label": "NewPriority",
            "cn1": str(incident.anomaly_count),
            "cn1Label": "AnomalyCount",
            "src": ",".join(incident.src_ips) if incident.src_ips else "",
            "dst": ",".join(incident.dst_ips) if incident.dst_ips else "",
            "msg": f"Incident escalated from {old_priority} to {incident.priority.value}",
        }

        cef_message = self._build_cef_message(
            signature_id="ICS-ESCALATION",
            name=f"Priority Escalation: {old_priority} -> {incident.priority.value}",
            severity=cef_severity,
            extensions=extensions,
        )

        syslog_severity = self._map_priority_to_syslog_severity(incident.priority)
        syslog_message = self._build_syslog_message(syslog_severity, cef_message)

        return await self._send_syslog(syslog_message)

    def _map_alert_to_syslog_severity(self, severity: AlertSeverity) -> SyslogSeverity:
        """Map alert severity to syslog severity."""
        mapping = {
            AlertSeverity.CRITICAL: SyslogSeverity.CRITICAL,
            AlertSeverity.HIGH: SyslogSeverity.ERROR,
            AlertSeverity.MEDIUM: SyslogSeverity.WARNING,
            AlertSeverity.LOW: SyslogSeverity.NOTICE,
        }
        return mapping.get(severity, SyslogSeverity.INFO)

    def _map_priority_to_syslog_severity(self, priority: IncidentPriority) -> SyslogSeverity:
        """Map incident priority to syslog severity."""
        mapping = {
            IncidentPriority.P1: SyslogSeverity.CRITICAL,
            IncidentPriority.P2: SyslogSeverity.ERROR,
            IncidentPriority.P3: SyslogSeverity.WARNING,
            IncidentPriority.P4: SyslogSeverity.NOTICE,
        }
        return mapping.get(priority, SyslogSeverity.INFO)

    async def _send_syslog(self, message: str) -> bool:
        """Send message to syslog server."""
        async with self._lock:
            try:
                sock = self._get_socket()
                encoded = message.encode("utf-8")

                if self.settings.protocol.lower() == "tcp":
                    # TCP: send with newline delimiter
                    sock.sendall(encoded + b"\n")
                else:
                    # UDP: send to address
                    sock.sendto(encoded, (self.settings.host, self.settings.port))

                logger.debug(
                    "syslog_sent",
                    host=self.settings.host,
                    port=self.settings.port,
                    protocol=self.settings.protocol,
                )
                return True

            except socket.timeout:
                logger.error(
                    "syslog_timeout",
                    host=self.settings.host,
                    port=self.settings.port,
                )
                self._socket = None
                return False

            except socket.error as e:
                logger.error(
                    "syslog_socket_error",
                    host=self.settings.host,
                    port=self.settings.port,
                    error=str(e),
                )
                self._socket = None
                return False
