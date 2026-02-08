"""Model storage abstraction for local and S3 backends."""

from src.config import StorageSettings, StoreType
from src.storage.base import ModelStore
from src.storage.local import LocalModelStore
from src.storage.s3 import S3ModelStore


def create_model_store(settings: StorageSettings) -> ModelStore:
    """Factory function to create the appropriate model store.

    Args:
        settings: Storage configuration settings.

    Returns:
        ModelStore instance based on store_type.

    Raises:
        ValueError: If store_type is not supported.
    """
    if settings.store_type == StoreType.LOCAL:
        return LocalModelStore(model_dir=settings.local_model_dir)
    elif settings.store_type == StoreType.S3:
        return S3ModelStore(
            bucket=settings.s3_bucket,
            prefix=settings.s3_prefix,
            region=settings.s3_region,
            cache_dir=settings.cache_dir,
        )
    else:
        raise ValueError(f"Unsupported store type: {settings.store_type}")


__all__ = [
    "ModelStore",
    "LocalModelStore",
    "S3ModelStore",
    "create_model_store",
]
