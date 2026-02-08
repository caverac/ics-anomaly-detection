"""Alerting service main entry point."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from src.config import Settings
from src.correlation.engine import CorrelationEngine
from src.deduplication.tracker import DeduplicationTracker
from src.escalation.manager import EscalationManager
from src.kafka.consumer import AnomalyConsumer
from src.kafka.producer import AlertProducer
from src.notifications.base import NotificationManager
from src.notifications.console import ConsoleNotifier
from src.notifications.slack import SlackNotifier
from src.notifications.splunk import SplunkNotifier
from src.notifications.syslog import SyslogNotifier
from src.notifications.webhook import WebhookNotifier
from src.schemas.alert import Alert, AlertStatus
from src.schemas.incident import Incident, IncidentStatus
from src.storage.redis_store import RedisStore

logger = structlog.get_logger()


class AlertingService:
    """Main alerting service application."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the alerting service."""
        self.settings = settings
        self.running = False

        # Core components
        self.consumer = AnomalyConsumer(settings.kafka)
        self.producer = AlertProducer(settings.kafka)
        self.store = RedisStore(settings.redis)

        # Processing components
        self.correlation = CorrelationEngine(settings.correlation, self.store)
        self.dedup = DeduplicationTracker(settings.deduplication, self.store)
        self.escalation = EscalationManager(settings.escalation)

        # Notification manager
        self.notifications = NotificationManager()
        self._setup_notifications()

        # Statistics
        self._alerts_processed = 0
        self._last_stats_time = datetime.now()

    def _setup_notifications(self) -> None:
        """Set up notification channels."""
        # Always add console notifier
        self.notifications.add_channel(ConsoleNotifier(enabled=True))

        # Add webhook if configured
        if self.settings.webhook.enabled:
            self.notifications.add_channel(WebhookNotifier(self.settings.webhook))

        # Add Slack if configured
        if self.settings.slack.enabled:
            self.notifications.add_channel(SlackNotifier(self.settings.slack))

        # Add Splunk HEC if configured
        if self.settings.splunk.enabled:
            self.notifications.add_channel(SplunkNotifier(self.settings.splunk))

        # Add Syslog if configured
        if self.settings.syslog.enabled:
            self.notifications.add_channel(SyslogNotifier(self.settings.syslog))

    def connect(self) -> None:
        """Connect to external services."""
        self.store.connect()
        self.consumer.connect()
        self.producer.connect()
        logger.info("alerting_service_connected")

    def close(self) -> None:
        """Close all connections."""
        self.producer.close()
        self.consumer.close()
        self.store.close()
        logger.info("alerting_service_closed")

    def is_kafka_connected(self) -> bool:
        """Check if Kafka is connected."""
        return self.consumer._consumer is not None

    def get_stats(self) -> dict[str, Any]:
        """Get combined service statistics."""
        correlation_stats = self.correlation.get_stats()
        dedup_stats = self.dedup.get_stats()
        escalation_stats = self.escalation.get_stats()
        notification_stats = self.notifications.get_stats()
        producer_stats = self.producer.get_stats()

        return {
            "alerts_processed": self._alerts_processed,
            "incidents_created": correlation_stats["incidents_created"],
            "incidents_updated": correlation_stats["incidents_updated"],
            "dedup_suppressed": dedup_stats["suppressed"],
            "dedup_allowed": dedup_stats["allowed"],
            "escalations": escalation_stats["escalations"],
            "notifications_sent": notification_stats["sent"],
            "notification_errors": notification_stats["errors"],
            "kafka_delivered": producer_stats["delivered"],
            "kafka_errors": producer_stats["errors"],
        }

    async def process_anomalies(self) -> None:
        """Main loop for processing anomalies."""
        logger.info(
            "alerting_processor_starting",
            input_topic=self.settings.kafka.input_topic,
            output_topic=self.settings.kafka.output_topic,
        )

        self.running = True

        while self.running:
            try:
                # Non-blocking poll
                anomaly = self.consumer.poll_one(timeout=0.1)

                if anomaly is None:
                    await asyncio.sleep(0.01)  # Yield to event loop
                    continue

                # Skip normal classifications
                if anomaly.classification.lower() == "normal":
                    continue

                # Correlate anomaly into alert and incident
                alert, incident = self.correlation.process_anomaly(anomaly)

                # Check deduplication
                if self.dedup.should_suppress(alert):
                    continue

                # Check for escalation
                old_priority = incident.priority
                new_priority = self.escalation.evaluate_escalation(incident, alert)

                if new_priority != old_priority:
                    incident.priority = new_priority
                    self.store.update_incident(incident)

                    # Send escalation notification
                    await self.notifications.notify_escalation(
                        incident, old_priority.value
                    )

                # Produce alert to Kafka
                self.producer.produce(alert)

                # Send alert notification
                await self.notifications.notify_alert(alert, incident)

                self._alerts_processed += 1

                # Periodic stats logging
                now = datetime.now()
                if (now - self._last_stats_time).seconds >= 30:
                    stats = self.get_stats()
                    logger.info("processing_stats", **stats)
                    self._last_stats_time = now

            except Exception as e:
                logger.error("processing_error", error=str(e))
                await asyncio.sleep(1)  # Back off on errors

        logger.info(
            "alerting_processor_stopped",
            total_alerts=self._alerts_processed,
        )


# Response models
class HealthResponse(BaseModel):
    status: str
    kafka_connected: bool
    redis_connected: bool


class StatsResponse(BaseModel):
    alerts_processed: int
    incidents_created: int
    incidents_updated: int
    notifications_sent: int
    dedup_suppressed: int
    escalations: int


class AcknowledgeResponse(BaseModel):
    id: str
    status: str
    acknowledged: bool


def configure_logging(settings: Settings) -> None:
    """Configure structured logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, settings.log_level.upper()))
        root_logger.addHandler(handler)

    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    settings = Settings()
    configure_logging(settings)

    service: AlertingService | None = None
    processing_task: asyncio.Task | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal service, processing_task

        service = AlertingService(settings)
        service.connect()
        app.state.service = service

        # Start processing task
        processing_task = asyncio.create_task(service.process_anomalies())

        yield

        # Shutdown
        if service:
            service.running = False
        if processing_task:
            processing_task.cancel()
            try:
                await processing_task
            except asyncio.CancelledError:
                pass
        if service:
            service.close()

    app = FastAPI(
        title="ICS Alerting Service",
        description="Alert management for ICS anomaly detection",
        version="0.1.0",
        lifespan=lifespan,
    )

    def get_service(request: Request) -> AlertingService:
        """Get the service instance from app state."""
        svc = getattr(request.app.state, "service", None)
        if not svc:
            raise HTTPException(status_code=503, detail="Service not initialized")
        return svc

    # Health and metrics endpoints
    @app.get("/health", response_model=HealthResponse)
    async def health_check(request: Request) -> HealthResponse:
        svc = get_service(request)
        redis_ok = svc.store.health_check()
        kafka_ok = svc.is_kafka_connected()
        status = "healthy" if redis_ok and kafka_ok else "degraded"
        return HealthResponse(
            status=status,
            kafka_connected=kafka_ok,
            redis_connected=redis_ok,
        )

    @app.get("/metrics")
    async def get_metrics(request: Request) -> dict[str, Any]:
        svc = get_service(request)
        stats = svc.get_stats()
        return {
            "alerting_alerts_processed_total": stats.get("alerts_processed", 0),
            "alerting_incidents_created_total": stats.get("incidents_created", 0),
            "alerting_incidents_updated_total": stats.get("incidents_updated", 0),
            "alerting_notifications_sent_total": stats.get("notifications_sent", 0),
            "alerting_alerts_suppressed_total": stats.get("dedup_suppressed", 0),
            "alerting_escalations_total": stats.get("escalations", 0),
        }

    @app.get("/stats", response_model=StatsResponse)
    async def get_stats(request: Request) -> StatsResponse:
        svc = get_service(request)
        stats = svc.get_stats()
        return StatsResponse(**stats)

    # Alert endpoints
    @app.get("/alerts", response_model=list[Alert])
    async def list_alerts(
        request: Request,
        limit: int = 50,
        status: AlertStatus | None = None,
        severity: str | None = None,
    ) -> list[Alert]:
        svc = get_service(request)
        return svc.store.list_alerts(limit=limit, status=status, severity=severity)

    @app.get("/alerts/{alert_id}", response_model=Alert)
    async def get_alert(request: Request, alert_id: str) -> Alert:
        svc = get_service(request)
        alert = svc.store.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return alert

    @app.post("/alerts/{alert_id}/acknowledge", response_model=AcknowledgeResponse)
    async def acknowledge_alert(request: Request, alert_id: str) -> AcknowledgeResponse:
        svc = get_service(request)
        success = svc.store.update_alert_status(alert_id, AlertStatus.ACKNOWLEDGED)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        return AcknowledgeResponse(
            id=alert_id,
            status=AlertStatus.ACKNOWLEDGED.value,
            acknowledged=True,
        )

    @app.post("/alerts/{alert_id}/resolve", response_model=AcknowledgeResponse)
    async def resolve_alert(request: Request, alert_id: str) -> AcknowledgeResponse:
        svc = get_service(request)
        success = svc.store.update_alert_status(alert_id, AlertStatus.RESOLVED)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        return AcknowledgeResponse(
            id=alert_id,
            status=AlertStatus.RESOLVED.value,
            acknowledged=True,
        )

    # Incident endpoints
    @app.get("/incidents", response_model=list[Incident])
    async def list_incidents(
        request: Request,
        limit: int = 50,
        status: IncidentStatus | None = None,
    ) -> list[Incident]:
        svc = get_service(request)
        return svc.store.list_incidents(limit=limit, status=status)

    @app.get("/incidents/{incident_id}", response_model=Incident)
    async def get_incident(request: Request, incident_id: str) -> Incident:
        svc = get_service(request)
        incident = svc.store.get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        return incident

    @app.post("/incidents/{incident_id}/acknowledge", response_model=AcknowledgeResponse)
    async def acknowledge_incident(
        request: Request, incident_id: str
    ) -> AcknowledgeResponse:
        svc = get_service(request)
        success = svc.store.update_incident_status(incident_id, IncidentStatus.ACKNOWLEDGED)
        if not success:
            raise HTTPException(status_code=404, detail="Incident not found")
        return AcknowledgeResponse(
            id=incident_id,
            status=IncidentStatus.ACKNOWLEDGED.value,
            acknowledged=True,
        )

    @app.post("/incidents/{incident_id}/resolve", response_model=AcknowledgeResponse)
    async def resolve_incident(
        request: Request, incident_id: str
    ) -> AcknowledgeResponse:
        svc = get_service(request)
        success = svc.store.update_incident_status(incident_id, IncidentStatus.RESOLVED)
        if not success:
            raise HTTPException(status_code=404, detail="Incident not found")
        return AcknowledgeResponse(
            id=incident_id,
            status=IncidentStatus.RESOLVED.value,
            acknowledged=True,
        )

    return app


def main() -> int:
    """Main entry point."""
    try:
        settings = Settings()
        configure_logging(settings)

        logger.info(
            "alerting_service_starting",
            host=settings.api.host,
            port=settings.api.port,
        )

        app = create_app()
        uvicorn.run(
            app,
            host=settings.api.host,
            port=settings.api.port,
            log_level=settings.log_level.lower(),
        )
        return 0

    except KeyboardInterrupt:
        logger.info("keyboard_interrupt")
        return 0
    except Exception as e:
        logger.error("fatal_error", error=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
