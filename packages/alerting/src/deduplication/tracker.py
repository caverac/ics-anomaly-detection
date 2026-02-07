"""Deduplication tracker for suppressing duplicate alerts."""

import structlog

from src.config import DeduplicationSettings
from src.schemas.alert import Alert
from src.storage.redis_store import RedisStore

logger = structlog.get_logger()


class DeduplicationTracker:
    """Tracks and suppresses duplicate alerts."""

    def __init__(self, settings: DeduplicationSettings, store: RedisStore) -> None:
        """Initialize the deduplication tracker."""
        self.settings = settings
        self.store = store
        self._suppressed_count = 0
        self._allowed_count = 0

    def should_suppress(self, alert: Alert) -> bool:
        """Check if an alert should be suppressed as a duplicate.

        Args:
            alert: The alert to check.

        Returns:
            True if the alert should be suppressed, False if it should be sent.
        """
        dedup_key = alert.get_dedup_key()

        is_duplicate = self.store.check_dedup(
            dedup_key,
            self.settings.suppression_seconds,
        )

        if is_duplicate:
            self._suppressed_count += 1
            logger.debug(
                "alert_suppressed",
                alert_id=alert.id,
                dedup_key=dedup_key,
                reason="duplicate",
            )
            return True

        self._allowed_count += 1
        return False

    def clear_suppression(self, alert: Alert) -> None:
        """Clear the suppression for a specific alert key.

        Use this when an alert is acknowledged or resolved.
        """
        dedup_key = alert.get_dedup_key()
        self.store.clear_dedup(dedup_key)
        logger.debug("dedup_cleared", dedup_key=dedup_key)

    def get_stats(self) -> dict[str, int]:
        """Get deduplication statistics."""
        return {
            "suppressed": self._suppressed_count,
            "allowed": self._allowed_count,
        }
