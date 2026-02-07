"""Redis storage for incidents and alerts."""

import json
from datetime import datetime

import redis
import structlog

from src.config import RedisSettings
from src.schemas.alert import Alert, AlertStatus
from src.schemas.incident import Incident, IncidentStatus

logger = structlog.get_logger()


class RedisStore:
    """Redis-backed storage for alerts and incidents."""

    # Key prefixes
    ALERT_PREFIX = "alert:"
    INCIDENT_PREFIX = "incident:"
    INCIDENT_BY_KEY_PREFIX = "incident:key:"
    DEDUP_PREFIX = "dedup:"
    ALERT_LIST = "alerts:list"
    INCIDENT_LIST = "incidents:list"

    def __init__(self, settings: RedisSettings) -> None:
        """Initialize Redis store."""
        self.settings = settings
        self._client: redis.Redis | None = None

    def connect(self) -> None:
        """Connect to Redis."""
        self._client = redis.from_url(
            self.settings.url,
            db=self.settings.db,
            decode_responses=True,
        )
        # Test connection
        self._client.ping()
        logger.info("redis_connected", url=self.settings.url)

    def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            self._client.close()
            logger.info("redis_closed")

    @property
    def client(self) -> redis.Redis:
        """Get Redis client."""
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    # Alert operations

    def save_alert(self, alert: Alert) -> None:
        """Save an alert to Redis."""
        key = f"{self.ALERT_PREFIX}{alert.id}"
        data = json.dumps(alert.to_redis())

        pipe = self.client.pipeline()
        pipe.set(key, data, ex=self.settings.alert_ttl_seconds)
        pipe.lpush(self.ALERT_LIST, alert.id)
        pipe.ltrim(self.ALERT_LIST, 0, 999)  # Keep last 1000 alerts
        pipe.execute()

        logger.debug("alert_saved", alert_id=alert.id)

    def get_alert(self, alert_id: str) -> Alert | None:
        """Get an alert by ID."""
        key = f"{self.ALERT_PREFIX}{alert_id}"
        data = self.client.get(key)

        if not data:
            return None

        return Alert.from_redis(json.loads(data))

    def update_alert_status(self, alert_id: str, status: AlertStatus) -> bool:
        """Update an alert's status."""
        alert = self.get_alert(alert_id)
        if not alert:
            return False

        alert.status = status
        key = f"{self.ALERT_PREFIX}{alert_id}"
        self.client.set(
            key,
            json.dumps(alert.to_redis()),
            ex=self.settings.alert_ttl_seconds,
        )
        return True

    def list_alerts(
        self,
        limit: int = 50,
        status: AlertStatus | None = None,
        severity: str | None = None,
    ) -> list[Alert]:
        """List recent alerts with optional filtering."""
        alert_ids = self.client.lrange(self.ALERT_LIST, 0, limit * 2)
        alerts = []

        for alert_id in alert_ids:
            if len(alerts) >= limit:
                break

            alert = self.get_alert(alert_id)
            if not alert:
                continue

            if status and alert.status != status:
                continue
            if severity and alert.severity.value != severity:
                continue

            alerts.append(alert)

        return alerts

    # Incident operations

    def save_incident(self, incident: Incident) -> None:
        """Save an incident to Redis."""
        key = f"{self.INCIDENT_PREFIX}{incident.id}"
        key_index = f"{self.INCIDENT_BY_KEY_PREFIX}{incident.correlation_key}"
        data = json.dumps(incident.to_redis())

        pipe = self.client.pipeline()
        pipe.set(key, data, ex=self.settings.incident_ttl_seconds)
        pipe.set(key_index, incident.id, ex=self.settings.incident_ttl_seconds)
        pipe.lpush(self.INCIDENT_LIST, incident.id)
        pipe.ltrim(self.INCIDENT_LIST, 0, 499)  # Keep last 500 incidents
        pipe.execute()

        logger.debug("incident_saved", incident_id=incident.id)

    def get_incident(self, incident_id: str) -> Incident | None:
        """Get an incident by ID."""
        key = f"{self.INCIDENT_PREFIX}{incident_id}"
        data = self.client.get(key)

        if not data:
            return None

        return Incident.from_redis(json.loads(data))

    def get_incident_by_correlation_key(self, correlation_key: str) -> Incident | None:
        """Get an active incident by correlation key."""
        key_index = f"{self.INCIDENT_BY_KEY_PREFIX}{correlation_key}"
        incident_id = self.client.get(key_index)

        if not incident_id:
            return None

        incident = self.get_incident(incident_id)
        if incident and incident.status == IncidentStatus.ACTIVE:
            return incident

        return None

    def update_incident(self, incident: Incident) -> None:
        """Update an existing incident."""
        incident.updated_at = datetime.utcnow()
        key = f"{self.INCIDENT_PREFIX}{incident.id}"
        self.client.set(
            key,
            json.dumps(incident.to_redis()),
            ex=self.settings.incident_ttl_seconds,
        )

    def update_incident_status(self, incident_id: str, status: IncidentStatus) -> bool:
        """Update an incident's status."""
        incident = self.get_incident(incident_id)
        if not incident:
            return False

        incident.status = status
        incident.updated_at = datetime.utcnow()
        self.update_incident(incident)
        return True

    def list_incidents(
        self,
        limit: int = 50,
        status: IncidentStatus | None = None,
    ) -> list[Incident]:
        """List recent incidents with optional filtering."""
        incident_ids = self.client.lrange(self.INCIDENT_LIST, 0, limit * 2)
        incidents = []

        for incident_id in incident_ids:
            if len(incidents) >= limit:
                break

            incident = self.get_incident(incident_id)
            if not incident:
                continue

            if status and incident.status != status:
                continue

            incidents.append(incident)

        return incidents

    # Deduplication operations

    def check_dedup(self, dedup_key: str, ttl_seconds: int) -> bool:
        """Check if a key is deduplicated (recently seen).

        Returns:
            True if the key was recently seen (should suppress), False otherwise.
        """
        key = f"{self.DEDUP_PREFIX}{dedup_key}"
        if self.client.exists(key):
            return True

        # Set the key with TTL
        self.client.set(key, "1", ex=ttl_seconds)
        return False

    def clear_dedup(self, dedup_key: str) -> None:
        """Clear a deduplication key."""
        key = f"{self.DEDUP_PREFIX}{dedup_key}"
        self.client.delete(key)

    # Health check

    def health_check(self) -> bool:
        """Check Redis connectivity."""
        try:
            self.client.ping()
            return True
        except Exception:
            return False

    def __enter__(self) -> "RedisStore":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()
