"""Local filesystem model storage."""

import shutil
from pathlib import Path

import structlog

from src.storage.base import ModelStore

logger = structlog.get_logger()


class LocalModelStore(ModelStore):
    """Model storage using local filesystem.

    This is the default storage backend, suitable for:
    - Local development
    - Docker deployments with mounted volumes
    - Testing
    """

    def __init__(self, model_dir: Path) -> None:
        """Initialize local model store.

        Args:
            model_dir: Directory where models are stored.
        """
        self._model_dir = Path(model_dir)

    def get_model_dir(self) -> Path:
        """Get the model directory path."""
        return self._model_dir

    def download_models(self) -> Path:
        """No-op for local storage - models are already local.

        Returns:
            The model directory path.

        Raises:
            FileNotFoundError: If model directory doesn't exist.
        """
        if not self._model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {self._model_dir}")

        logger.info(
            "local_models_ready",
            model_dir=str(self._model_dir),
            files=self.list_models(),
        )
        return self._model_dir

    def upload_models(self, local_dir: Path) -> None:
        """Copy models from local_dir to model directory.

        Args:
            local_dir: Source directory containing model files.

        Raises:
            FileNotFoundError: If local_dir doesn't exist.
        """
        local_dir = Path(local_dir)
        if not local_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {local_dir}")

        # Create model directory if needed
        self._model_dir.mkdir(parents=True, exist_ok=True)

        # Copy all files
        copied_files = []
        for src_file in local_dir.iterdir():
            if src_file.is_file():
                dst_file = self._model_dir / src_file.name
                shutil.copy2(src_file, dst_file)
                copied_files.append(src_file.name)

        logger.info(
            "models_copied",
            source=str(local_dir),
            destination=str(self._model_dir),
            files=copied_files,
        )

    def model_exists(self, filename: str) -> bool:
        """Check if a model file exists."""
        return (self._model_dir / filename).exists()

    def list_models(self) -> list[str]:
        """List all model files in the directory."""
        if not self._model_dir.exists():
            return []
        return [f.name for f in self._model_dir.iterdir() if f.is_file()]

    @property
    def store_type(self) -> str:
        """Return storage type identifier."""
        return "local"
