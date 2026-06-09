"""
Vision — MinIO Storage Layer.

Uploads incoming files to MinIO immediately, returns a storage reference.
Background workers download from MinIO for processing. Keeps the API fast
and files durable regardless of processing outcome.
"""

from __future__ import annotations

import os
import uuid
from datetime import timedelta
from pathlib import Path

from minio import Minio
from minio.error import S3Error

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "127.0.0.1:9002")
_MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
_MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
_MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "vision-uploads")
_MINIO_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"


def _get_client() -> Minio:
    return Minio(
        _MINIO_ENDPOINT,
        access_key=_MINIO_ACCESS_KEY,
        secret_key=_MINIO_SECRET_KEY,
        secure=_MINIO_SECURE,
    )


def ensure_bucket() -> str:
    """Create the upload bucket if it doesn't exist. Idempotent."""
    client = _get_client()
    if not client.bucket_exists(_MINIO_BUCKET):
        client.make_bucket(_MINIO_BUCKET)
    return _MINIO_BUCKET


def upload_file(file_path: str | Path, original_name: str | None = None) -> dict:
    """Upload a file to MinIO. Returns the storage reference.

    The object key is a UUID-prefixed path to avoid collisions:
        {uuid}/{original_name}

    Returns:
        {"bucket": str, "object_key": str, "original_name": str, "size_bytes": int}
    """
    file_path = Path(file_path)
    if original_name is None:
        original_name = file_path.name

    ensure_bucket()
    client = _get_client()

    object_key = f"{uuid.uuid4().hex[:12]}/{original_name}"
    file_size = file_path.stat().st_size

    client.fput_object(
        _MINIO_BUCKET,
        object_key,
        str(file_path),
    )

    return {
        "bucket": _MINIO_BUCKET,
        "object_key": object_key,
        "original_name": original_name,
        "size_bytes": file_size,
    }


def download_file(bucket: str, object_key: str, dest_path: str | Path) -> Path:
    """Download a file from MinIO to a local path. Returns the destination path."""
    dest_path = Path(dest_path)
    client = _get_client()
    client.fget_object(bucket, object_key, str(dest_path))
    return dest_path


def delete_file(bucket: str, object_key: str) -> bool:
    """Delete a file from MinIO. Returns True if successful."""
    client = _get_client()
    try:
        client.remove_object(bucket, object_key)
        return True
    except S3Error:
        return False


def get_public_url(bucket: str, object_key: str, expires_seconds: int = 3600) -> str:
    """Generate a presigned URL for viewing. Valid for expires_seconds (default 1 hour)."""
    client = _get_client()
    return client.presigned_get_object(
        bucket, object_key,
        expires=timedelta(seconds=expires_seconds),
        response_headers={"response-content-disposition": "inline"},
    )
