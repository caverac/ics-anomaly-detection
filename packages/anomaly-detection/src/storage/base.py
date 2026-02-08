"""Abstract base class for model storage."""

from abc import ABC, abstractmethod
from pathlib import Path


class ModelStore(ABC):
    """Abstract interface for model storage backends.

    Provides a unified interface for loading and saving models
    from different storage backends (local filesystem, S3, etc.).
    """

    @abstractmethod
    def get_model_dir(self) -> Path:
        """Get the local directory where models are available.

        For local storage, this is the model directory itself.
        For remote storage (S3), this is the local cache after download.

        Returns:
            Path to directory containing model files.
        """
        ...

    @abstractmethod
    def download_models(self) -> Path:
        """Download models from remote storage to local cache.

        For local storage, this is a no-op that returns the model dir.
        For remote storage, downloads all model files to cache.

        Returns:
            Path to directory containing downloaded model files.

        Raises:
            FileNotFoundError: If models don't exist in storage.
            ConnectionError: If unable to connect to remote storage.
        """
        ...

    @abstractmethod
    def upload_models(self, local_dir: Path) -> None:
        """Upload models from local directory to remote storage.

        For local storage, this copies files to the model directory.
        For remote storage, uploads all files to the remote location.

        Args:
            local_dir: Local directory containing model files to upload.

        Raises:
            FileNotFoundError: If local_dir doesn't exist.
            ConnectionError: If unable to connect to remote storage.
        """
        ...

    @abstractmethod
    def model_exists(self, filename: str) -> bool:
        """Check if a specific model file exists in storage.

        Args:
            filename: Name of the model file (e.g., 'normalizer.joblib').

        Returns:
            True if the file exists in storage.
        """
        ...

    @abstractmethod
    def list_models(self) -> list[str]:
        """List all model files in storage.

        Returns:
            List of model filenames.
        """
        ...

    @property
    @abstractmethod
    def store_type(self) -> str:
        """Get the storage type identifier.

        Returns:
            String identifier (e.g., 'local', 's3').
        """
        ...
