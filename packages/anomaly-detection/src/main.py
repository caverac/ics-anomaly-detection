"""Anomaly detection main entry point."""

import logging
import signal
import sys
from datetime import datetime
from typing import Any

import structlog

from src.config import Settings
from src.inference.engine import InferenceEngine
from src.kafka.consumer import FeatureConsumer
from src.kafka.producer import AnomalyProducer
from src.schemas.anomaly import Classification

logger = structlog.get_logger()


class AnomalyDetector:
    """Main anomaly detection application."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the detector.

        Args:
            settings: Application settings.
        """
        self.settings = settings
        self.running = False

        self.consumer = FeatureConsumer(settings.kafka)
        self.producer = AnomalyProducer(settings.kafka)
        self.engine = InferenceEngine(settings.model)

        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Set up graceful shutdown handlers."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        logger.info("shutdown_signal_received", signal=signum)
        self.running = False

    def run(self) -> None:
        """Run the main processing loop."""
        if not self.engine.load_models():
            logger.error("failed_to_load_models")
            return

        self.engine.start_hot_reload()
        self.running = True

        messages_processed = 0
        anomalies_detected = 0
        last_stats_time = datetime.now()

        logger.info(
            "anomaly_detector_starting",
            input_topic=self.settings.kafka.input_topic,
            output_topic=self.settings.kafka.output_topic,
        )

        with self.consumer, self.producer:
            for feature_vector in self.consumer.consume(timeout=1.0):
                if not self.running:
                    break

                try:
                    result = self.engine.predict(feature_vector)

                    self.producer.produce(result)

                    messages_processed += 1
                    if result.classification != Classification.NORMAL:
                        anomalies_detected += 1

                        logger.info(
                            "anomaly_detected",
                            classification=result.classification.value,
                            score=f"{result.ensemble_score:.3f}",
                            type=result.anomaly_type.value if result.anomaly_type else None,
                            src_ip=result.window_key.src_ip,
                            dst_ip=result.window_key.dst_ip,
                        )

                    now = datetime.now()
                    if (now - last_stats_time).seconds >= 10:
                        engine_stats = self.engine.get_stats()
                        logger.info(
                            "processing_stats",
                            messages_processed=messages_processed,
                            anomalies_detected=anomalies_detected,
                            active_connections=engine_stats["sequence_builder"]["total_connections"],
                        )
                        last_stats_time = now

                except Exception as e:
                    logger.error("processing_error", error=str(e))

        self.engine.close()

        logger.info(
            "anomaly_detector_stopped",
            total_messages=messages_processed,
            total_anomalies=anomalies_detected,
        )


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


def main() -> int:
    """Main entry point."""
    try:
        settings = Settings()
        configure_logging(settings)

        detector = AnomalyDetector(settings)
        detector.run()
        return 0
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt")
        return 0
    except Exception as e:
        logger.error("fatal_error", error=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
