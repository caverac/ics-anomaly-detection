"""AWS S3 model storage."""

from pathlib import Path

import structlog

from src.storage.base import ModelStore

logger = structlog.get_logger()


class S3ModelStore(ModelStore):
    """Model storage using AWS S3.

    Suitable for:
    - Production deployments
    - Multi-environment model sharing
    - Model versioning and rollback

    Models are downloaded to a local cache before loading.
    """

    def __init__(
        self,
        bucket: str,
        prefix: str = "models/",
        region: str = "us-east-1",
        cache_dir: Path = Path("/tmp/ics-models"),
    ) -> None:
        """Initialize S3 model store.

        Args:
            bucket: S3 bucket name.
            prefix: S3 key prefix for models (e.g., 'models/v1.0.0/').
            region: AWS region.
            cache_dir: Local directory for caching downloaded models.
        """
        self._bucket = bucket
        self._prefix = prefix.rstrip("/") + "/" if prefix else ""
        self._region = region
        self._cache_dir = Path(cache_dir)
        self._client = None

    def _get_client(self):
        """Lazy-load boto3 client."""
        if self._client is None:
            try:
                import boto3
            except ImportError as err:
                raise ImportError(
                    "boto3 is required for S3 storage. "
                    "Install with: pip install 'ics-anomaly-detection[aws]'"
                ) from err
            self._client = boto3.client("s3", region_name=self._region)
        return self._client

    def get_model_dir(self) -> Path:
        """Get the local cache directory where models are downloaded."""
        return self._cache_dir

    def download_models(self) -> Path:
        """Download all models from S3 to local cache.

        Returns:
            Path to cache directory containing downloaded models.

        Raises:
            FileNotFoundError: If no models found in S3.
            ConnectionError: If unable to connect to S3.
        """
        client = self._get_client()

        # Create cache directory
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        try:
            # List objects in the prefix
            response = client.list_objects_v2(
                Bucket=self._bucket,
                Prefix=self._prefix,
            )

            if "Contents" not in response or len(response["Contents"]) == 0:
                raise FileNotFoundError(
                    f"No models found in s3://{self._bucket}/{self._prefix}"
                )

            downloaded_files = []
            for obj in response["Contents"]:
                key = obj["Key"]
                # Extract filename from key
                filename = key[len(self._prefix) :]
                if not filename:  # Skip the prefix itself
                    continue

                local_path = self._cache_dir / filename
                local_path.parent.mkdir(parents=True, exist_ok=True)

                logger.debug("downloading_model", key=key, local_path=str(local_path))
                client.download_file(self._bucket, key, str(local_path))
                downloaded_files.append(filename)

            logger.info(
                "models_downloaded_from_s3",
                bucket=self._bucket,
                prefix=self._prefix,
                cache_dir=str(self._cache_dir),
                files=downloaded_files,
            )

            return self._cache_dir

        except client.exceptions.NoSuchBucket as err:
            raise ConnectionError(f"S3 bucket not found: {self._bucket}") from err
        except Exception as e:
            if "NoCredentialProviders" in str(e) or "InvalidAccessKeyId" in str(e):
                raise ConnectionError(f"AWS credentials error: {e}") from e
            raise

    def upload_models(self, local_dir: Path) -> None:
        """Upload models from local directory to S3.

        Args:
            local_dir: Local directory containing model files.

        Raises:
            FileNotFoundError: If local_dir doesn't exist.
            ConnectionError: If unable to connect to S3.
        """
        local_dir = Path(local_dir)
        if not local_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {local_dir}")

        client = self._get_client()

        uploaded_files = []
        for src_file in local_dir.iterdir():
            if src_file.is_file():
                key = f"{self._prefix}{src_file.name}"
                logger.debug("uploading_model", local_path=str(src_file), key=key)
                client.upload_file(str(src_file), self._bucket, key)
                uploaded_files.append(src_file.name)

        logger.info(
            "models_uploaded_to_s3",
            bucket=self._bucket,
            prefix=self._prefix,
            files=uploaded_files,
        )

    def model_exists(self, filename: str) -> bool:
        """Check if a model file exists in S3."""
        client = self._get_client()
        key = f"{self._prefix}{filename}"
        try:
            client.head_object(Bucket=self._bucket, Key=key)
            return True
        except client.exceptions.ClientError:
            return False

    def list_models(self) -> list[str]:
        """List all model files in S3 prefix."""
        client = self._get_client()
        try:
            response = client.list_objects_v2(
                Bucket=self._bucket,
                Prefix=self._prefix,
            )
            if "Contents" not in response:
                return []
            return [
                obj["Key"][len(self._prefix) :]
                for obj in response["Contents"]
                if obj["Key"] != self._prefix
            ]
        except Exception:
            return []

    @property
    def store_type(self) -> str:
        """Return storage type identifier."""
        return "s3"
