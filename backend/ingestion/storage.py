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
from urllib.parse import urlsplit, urlunsplit

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
# When set, presigned URLs returned to browsers are rewritten to this public
# host with HTTPS scheme. The internal client still signs against
# _MINIO_ENDPOINT; MinIO validates signatures independent of the Host header,
# so the path/query/signature survive the swap intact. If unset, behavior is
# unchanged (local dev: presigned URL uses _MINIO_ENDPOINT as-is).
_MINIO_PUBLIC_ENDPOINT = os.environ.get("MINIO_PUBLIC_ENDPOINT")


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


def upload_attachment(object_key: str, content: bytes) -> dict:
    """Upload raw bytes to MinIO under the given object key.

    Used by the Mailgun webhook for inbound email attachments — no local
    file involved, just bytes in memory.
    """
    from io import BytesIO

    ensure_bucket()
    client = _get_client()
    data = BytesIO(content)
    client.put_object(
        _MINIO_BUCKET,
        object_key,
        data,
        length=len(content),
    )
    return {"bucket": _MINIO_BUCKET, "object_key": object_key, "size_bytes": len(content)}


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


def _get_public_client() -> Minio | None:
    """Return a MinIO client scoped to the public endpoint for presigned URL signing.

    When MINIO_SERVER_URL is set, creates a client whose endpoint matches the
    public-facing URL so that presigned signatures include the correct Host
    header.  presigned_get_object() does NOT make a network call — it computes
    the signature locally — so the fact that the SDK cannot actually connect
    through this endpoint is irrelevant.
    """
    server_url = os.environ.get("MINIO_SERVER_URL")
    if not server_url:
        return None
    # Strip scheme; the endpoint is host-only (no port) so the presigned URL
    # matches exactly what the browser will request.
    parsed = urlsplit(server_url)
    host = parsed.netloc.split(":")[0]  # e.g. "files-vision.justicequest.pro"
    return Minio(
        host,
        access_key=_MINIO_ACCESS_KEY,
        secret_key=_MINIO_SECRET_KEY,
        secure=True,  # https scheme, default port 443 — matches browser request
    )


def get_public_url(bucket: str, object_key: str, expires_seconds: int = 3600) -> str:
    """Generate a presigned URL for viewing. Valid for expires_seconds (default 1 hour).

    When MINIO_SERVER_URL is set, signs with the public hostname so S3 Signature
    V4 includes the correct Host header — no host rewriting needed.  Falls back
    to the internal client + host rewrite for local dev.
    """
    public_client = _get_public_client()
    if public_client is not None:
        # Client is secure=True so URL is already https:// with the correct host.
        return public_client.presigned_get_object(
            bucket, object_key,
            expires=timedelta(seconds=expires_seconds),
            response_headers={"response-content-disposition": "inline"},
        )

    # Fallback: internal client + host rewrite (local dev / no MINIO_SERVER_URL).
    client = _get_client()
    url = client.presigned_get_object(
        bucket, object_key,
        expires=timedelta(seconds=expires_seconds),
        response_headers={"response-content-disposition": "inline"},
    )
    if _MINIO_PUBLIC_ENDPOINT:
        parts = urlsplit(url)
        public = _MINIO_PUBLIC_ENDPOINT
        if "://" in public:
            public = urlsplit(public).netloc
        url = urlunsplit((
            "https",
            public,
            parts.path,
            parts.query,
            parts.fragment,
        ))
    return url
