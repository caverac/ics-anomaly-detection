"""Feature engine main entry point."""

import signal
import sys
from datetime import datetime
from typing import Any

import structlog

from src.config import Settings
from src.extractors.base import extract_features
from src.features.vector import FeatureVector
from src.kafka.consumer import MessageConsumer
from src.kafka.producer import FeatureProducer
from src.windows.manager import WindowManager

logger = structlog.get_logger()


class FeatureEngine:
    """Main feature engine application."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.running = False

        # Initialize components
        self.consumer = MessageConsumer(settings.kafka)
        self.producer = FeatureProducer(settings.kafka)
        self.window_manager = WindowManager(settings.windows)

        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Set up graceful shutdown handlers."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        logger.info("shutdown_signal_received", signal=signum)
        self.running = False

    def _process_closed_windows(self) -> int:
        """Process all closed windows and publish features.

        Returns the number of windows processed.
        """
        closed_windows = self.window_manager.get_closed_windows()
        processed = 0

        for key, buffer in closed_windows:
            try:
                # Extract features
                features = extract_features(key, buffer)

                # Create feature vector
                vector = FeatureVector.from_features(features)

                # Publish to Kafka
                msg_key = f"{key.src_ip}:{key.dst_ip}:{key.protocol}"
                self.producer.produce(msg_key, vector.model_dump(mode="json"))

                processed += 1

                logger.debug(
                    "feature_vector_published",
                    protocol=vector.protocol,
                    message_count=vector.message_count,
                    window_size=vector.window_size_seconds,
                )
            except Exception as e:
                logger.error(
                    "feature_extraction_failed",
                    error=str(e),
                    window_key=str(key),
                )

        return processed

    def run(self) -> None:
        """Run the main processing loop."""
        self.running = True
        messages_processed = 0
        features_published = 0
        last_stats_time = datetime.now()

        logger.info(
            "feature_engine_starting",
            window_sizes=self.settings.windows.window_sizes,
            input_topics=self.settings.kafka.input_topics,
            output_topic=self.settings.kafka.output_topic,
        )

        with self.consumer, self.producer:
            for message in self.consumer.consume(timeout=1.0):
                if not self.running:
                    break

                try:
                    # Add message to window manager
                    self.window_manager.add_message(message)
                    messages_processed += 1

                    # Process closed windows periodically
                    features_published += self._process_closed_windows()

                    # Log stats every 10 seconds
                    now = datetime.now()
                    if (now - last_stats_time).seconds >= 10:
                        stats = self.window_manager.get_stats()
                        logger.info(
                            "processing_stats",
                            messages_processed=messages_processed,
                            features_published=features_published,
                            active_windows=stats["active_windows"],
                            buffered_messages=stats["total_buffered_messages"],
                        )
                        last_stats_time = now

                except Exception as e:
                    logger.error("processing_error", error=str(e))

        # Final flush - process any remaining windows
        final_published = self._process_closed_windows()
        features_published += final_published

        logger.info(
            "feature_engine_stopped",
            total_messages_processed=messages_processed,
            total_features_published=features_published,
        )


def configure_logging(settings: Settings) -> None:
    """Configure structured logging."""
    import logging
    import sys

    # Configure Python's stdlib logging first
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Add a stream handler if none exists
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, settings.log_level.upper()))
        root_logger.addHandler(handler)

    # Configure structlog
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

        engine = FeatureEngine(settings)
        engine.run()
        return 0
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt")
        return 0
    except Exception as e:
        logger.error("fatal_error", error=str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
