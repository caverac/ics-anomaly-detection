"""FastAPI routes for the alerting service."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.schemas.alert import Alert, AlertStatus
from src.schemas.incident import Incident, IncidentStatus
from src.storage.redis_store import RedisStore


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    kafka_connected: bool
    redis_connected: bool


class StatsResponse(BaseModel):
    """Service statistics response."""

    alerts_processed: int
    incidents_created: int
    incidents_updated: int
    notifications_sent: int
    dedup_suppressed: int
    escalations: int


class AcknowledgeResponse(BaseModel):
    """Acknowledgement response."""

    id: str
    status: str
    acknowledged: bool


def create_router(
    store: RedisStore,
    get_stats_fn: Any,
    kafka_connected_fn: Any,
) -> APIRouter:
    """Create the API router with dependencies.

    Args:
        store: Redis store instance.
        get_stats_fn: Function to get service statistics.
        kafka_connected_fn: Function to check Kafka connection.

    Returns:
        Configured FastAPI router.
    """
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """Check service health."""
        redis_ok = store.health_check()
        kafka_ok = kafka_connected_fn()

        status = "healthy" if redis_ok and kafka_ok else "degraded"

        return HealthResponse(
            status=status,
            kafka_connected=kafka_ok,
            redis_connected=redis_ok,
        )

    @router.get("/metrics")
    async def get_metrics() -> dict[str, Any]:
        """Get Prometheus-compatible metrics."""
        stats = get_stats_fn()

        return {
            "alerting_alerts_processed_total": stats.get("alerts_processed", 0),
            "alerting_incidents_created_total": stats.get("incidents_created", 0),
            "alerting_incidents_updated_total": stats.get("incidents_updated", 0),
            "alerting_notifications_sent_total": stats.get("notifications_sent", 0),
            "alerting_alerts_suppressed_total": stats.get("dedup_suppressed", 0),
            "alerting_escalations_total": stats.get("escalations", 0),
        }

    @router.get("/stats", response_model=StatsResponse)
    async def get_stats() -> StatsResponse:
        """Get service statistics."""
        stats = get_stats_fn()
        return StatsResponse(**stats)

    # Alert endpoints

    @router.get("/alerts", response_model=list[Alert])
    async def list_alerts(
        limit: int = 50,
        status: AlertStatus | None = None,
        severity: str | None = None,
    ) -> list[Alert]:
        """List recent alerts."""
        return store.list_alerts(limit=limit, status=status, severity=severity)

    @router.get("/alerts/{alert_id}", response_model=Alert)
    async def get_alert(alert_id: str) -> Alert:
        """Get a specific alert."""
        alert = store.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return alert

    @router.post("/alerts/{alert_id}/acknowledge", response_model=AcknowledgeResponse)
    async def acknowledge_alert(alert_id: str) -> AcknowledgeResponse:
        """Acknowledge an alert."""
        success = store.update_alert_status(alert_id, AlertStatus.ACKNOWLEDGED)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")

        return AcknowledgeResponse(
            id=alert_id,
            status=AlertStatus.ACKNOWLEDGED.value,
            acknowledged=True,
        )

    @router.post("/alerts/{alert_id}/resolve", response_model=AcknowledgeResponse)
    async def resolve_alert(alert_id: str) -> AcknowledgeResponse:
        """Resolve an alert."""
        success = store.update_alert_status(alert_id, AlertStatus.RESOLVED)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")

        return AcknowledgeResponse(
            id=alert_id,
            status=AlertStatus.RESOLVED.value,
            acknowledged=True,
        )

    # Incident endpoints

    @router.get("/incidents", response_model=list[Incident])
    async def list_incidents(
        limit: int = 50,
        status: IncidentStatus | None = None,
    ) -> list[Incident]:
        """List recent incidents."""
        return store.list_incidents(limit=limit, status=status)

    @router.get("/incidents/{incident_id}", response_model=Incident)
    async def get_incident(incident_id: str) -> Incident:
        """Get a specific incident."""
        incident = store.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        return incident

    @router.post("/incidents/{incident_id}/acknowledge", response_model=AcknowledgeResponse)
    async def acknowledge_incident(incident_id: str) -> AcknowledgeResponse:
        """Acknowledge an incident."""
        success = store.update_incident_status(incident_id, IncidentStatus.ACKNOWLEDGED)
        if not success:
            raise HTTPException(status_code=404, detail="Incident not found")

        return AcknowledgeResponse(
            id=incident_id,
            status=IncidentStatus.ACKNOWLEDGED.value,
            acknowledged=True,
        )

    @router.post("/incidents/{incident_id}/resolve", response_model=AcknowledgeResponse)
    async def resolve_incident(incident_id: str) -> AcknowledgeResponse:
        """Resolve an incident."""
        success = store.update_incident_status(incident_id, IncidentStatus.RESOLVED)
        if not success:
            raise HTTPException(status_code=404, detail="Incident not found")

        return AcknowledgeResponse(
            id=incident_id,
            status=IncidentStatus.RESOLVED.value,
            acknowledged=True,
        )

    return router
