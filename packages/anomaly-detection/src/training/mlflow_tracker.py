"""MLflow integration for experiment tracking."""

from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

try:
    import mlflow
    from mlflow.tracking import MlflowClient

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    mlflow = None
    MlflowClient = None


class MLflowTracker:
    """MLflow experiment tracker for training runs.

    Tracks parameters, metrics, and artifacts for model training.
    Gracefully handles missing MLflow dependency.
    """

    def __init__(
        self,
        tracking_uri: str = "http://localhost:5000",
        experiment_name: str = "ics-anomaly-detection",
    ) -> None:
        """Initialize the tracker.

        Args:
            tracking_uri: MLflow tracking server URI.
            experiment_name: Name of the experiment.
        """
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        self._run_id: str | None = None
        self._enabled = MLFLOW_AVAILABLE

        if self._enabled:
            try:
                mlflow.set_tracking_uri(tracking_uri)
                mlflow.set_experiment(experiment_name)
                logger.info(
                    "mlflow_initialized",
                    tracking_uri=tracking_uri,
                    experiment=experiment_name,
                )
            except Exception as e:
                logger.warning("mlflow_initialization_failed", error=str(e))
                self._enabled = False
        else:
            logger.info("mlflow_not_available", message="Training will proceed without tracking")

    @property
    def is_enabled(self) -> bool:
        """Check if MLflow tracking is enabled."""
        return self._enabled

    def start_run(self, run_name: str | None = None, tags: dict[str, str] | None = None) -> None:
        """Start a new MLflow run.

        Args:
            run_name: Optional name for the run.
            tags: Optional tags to add to the run.
        """
        if not self._enabled:
            return

        try:
            run = mlflow.start_run(run_name=run_name)
            self._run_id = run.info.run_id

            if tags:
                for key, value in tags.items():
                    mlflow.set_tag(key, value)

            logger.info("mlflow_run_started", run_id=self._run_id)
        except Exception as e:
            logger.warning("mlflow_start_run_failed", error=str(e))
            self._enabled = False

    def end_run(self, status: str = "FINISHED") -> None:
        """End the current MLflow run.

        Args:
            status: Run status (FINISHED, FAILED, KILLED).
        """
        if not self._enabled or not self._run_id:
            return

        try:
            mlflow.end_run(status=status)
            logger.info("mlflow_run_ended", run_id=self._run_id, status=status)
            self._run_id = None
        except Exception as e:
            logger.warning("mlflow_end_run_failed", error=str(e))

    def log_params(self, params: dict[str, Any]) -> None:
        """Log parameters to MLflow.

        Args:
            params: Dictionary of parameters.
        """
        if not self._enabled:
            return

        try:
            flat_params = self._flatten_dict(params)
            for key, value in flat_params.items():
                mlflow.log_param(key, value)
        except Exception as e:
            logger.warning("mlflow_log_params_failed", error=str(e))

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        """Log metrics to MLflow.

        Args:
            metrics: Dictionary of metric name to value.
            step: Optional step number for time-series metrics.
        """
        if not self._enabled:
            return

        try:
            for key, value in metrics.items():
                mlflow.log_metric(key, value, step=step)
        except Exception as e:
            logger.warning("mlflow_log_metrics_failed", error=str(e))

    def log_artifact(self, path: Path, artifact_path: str | None = None) -> None:
        """Log an artifact file to MLflow.

        Args:
            path: Local path to the artifact.
            artifact_path: Destination path in artifact store.
        """
        if not self._enabled:
            return

        try:
            mlflow.log_artifact(str(path), artifact_path)
            logger.info("mlflow_artifact_logged", path=str(path))
        except Exception as e:
            logger.warning("mlflow_log_artifact_failed", error=str(e))

    def log_model_summary(self, model_name: str, params: dict[str, Any]) -> None:
        """Log a model summary.

        Args:
            model_name: Name of the model.
            params: Model parameters.
        """
        if not self._enabled:
            return

        prefixed = {f"{model_name}.{k}": v for k, v in params.items()}
        self.log_params(prefixed)

    def _flatten_dict(
        self, d: dict[str, Any], parent_key: str = "", sep: str = "."
    ) -> dict[str, Any]:
        """Flatten nested dictionary.

        Args:
            d: Dictionary to flatten.
            parent_key: Prefix for keys.
            sep: Separator between nested keys.

        Returns:
            Flattened dictionary.
        """
        items: list[tuple[str, Any]] = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def __enter__(self) -> "MLflowTracker":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        if exc_type is not None:
            self.end_run(status="FAILED")
        else:
            self.end_run(status="FINISHED")
