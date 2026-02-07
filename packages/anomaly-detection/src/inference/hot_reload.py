"""Hot reload support for model updates."""

import threading
import time
from pathlib import Path
from typing import Callable

import structlog

from src.models.ensemble import EnsembleModel

logger = structlog.get_logger()


class ModelWatcher:
    """Watches model directory for changes and triggers reloads.

    Uses file modification time to detect changes. Provides thread-safe
    model reloading without service interruption.
    """

    def __init__(
        self,
        model_dir: Path,
        check_interval: float = 30.0,
        on_reload: Callable[[EnsembleModel], None] | None = None,
    ) -> None:
        """Initialize the model watcher.

        Args:
            model_dir: Directory containing model files.
            check_interval: Seconds between checks for changes.
            on_reload: Callback to invoke when models are reloaded.
        """
        self.model_dir = model_dir
        self.check_interval = check_interval
        self.on_reload = on_reload

        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._last_mtimes: dict[str, float] = {}
        self._current_ensemble: EnsembleModel | None = None

        self._model_files = [
            "isolation_forest.joblib",
            "one_class_svm.joblib",
            "lstm_autoencoder.pt",
            "normalizer.joblib",
        ]

    def start(self, initial_ensemble: EnsembleModel | None = None) -> None:
        """Start the watcher thread.

        Args:
            initial_ensemble: Initial ensemble to use.
        """
        if self._running:
            return

        self._current_ensemble = initial_ensemble
        self._update_mtimes()
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        logger.info("model_watcher_started", model_dir=str(self.model_dir))

    def stop(self) -> None:
        """Stop the watcher thread."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("model_watcher_stopped")

    def get_ensemble(self) -> EnsembleModel | None:
        """Get the current ensemble model.

        Thread-safe accessor for the current ensemble.

        Returns:
            Current EnsembleModel or None if not loaded.
        """
        with self._lock:
            return self._current_ensemble

    def force_reload(self) -> bool:
        """Force an immediate reload of models.

        Returns:
            True if reload succeeded, False otherwise.
        """
        return self._reload_models()

    def _watch_loop(self) -> None:
        """Main watch loop running in background thread."""
        while self._running:
            time.sleep(self.check_interval)
            if not self._running:
                break

            if self._check_for_changes():
                logger.info("model_changes_detected")
                if self._reload_models():
                    logger.info("models_reloaded_successfully")
                else:
                    logger.warning("model_reload_failed")

    def _update_mtimes(self) -> None:
        """Update stored modification times for all model files."""
        for filename in self._model_files:
            path = self.model_dir / filename
            if path.exists():
                self._last_mtimes[filename] = path.stat().st_mtime
            else:
                self._last_mtimes[filename] = 0.0

    def _check_for_changes(self) -> bool:
        """Check if any model files have been modified.

        Returns:
            True if changes detected, False otherwise.
        """
        for filename in self._model_files:
            path = self.model_dir / filename
            if path.exists():
                current_mtime = path.stat().st_mtime
                if current_mtime != self._last_mtimes.get(filename, 0.0):
                    return True
            elif filename in self._last_mtimes and self._last_mtimes[filename] > 0:
                return True
        return False

    def _reload_models(self) -> bool:
        """Reload models from disk.

        Creates a new ensemble and atomically swaps it with the current one.

        Returns:
            True if reload succeeded, False otherwise.
        """
        try:
            new_ensemble = EnsembleModel()
            new_ensemble.load_models(self.model_dir)

            if not new_ensemble.is_fitted:
                logger.warning("reloaded_ensemble_not_fitted")
                return False

            with self._lock:
                old_ensemble = self._current_ensemble
                self._current_ensemble = new_ensemble

            self._update_mtimes()

            if self.on_reload is not None:
                self.on_reload(new_ensemble)

            if old_ensemble is not None:
                old_ensemble.close()

            return True

        except Exception as e:
            logger.error("model_reload_error", error=str(e))
            return False

    def __enter__(self) -> "ModelWatcher":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.stop()
