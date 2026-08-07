"""MinIO client + bucket bootstrap."""

from __future__ import annotations

from minio import Minio

from .core.config import get_settings

_settings = get_settings()

client = Minio(
    _settings.minio_endpoint,
    access_key=_settings.minio_access_key,
    secret_key=_settings.minio_secret_key,
    secure=_settings.minio_secure,
)

# Same credentials, different host: only used to *sign* URLs a browser will
# actually call. Internal admin calls (bucket_exists, make_bucket) stay on
# `client` above — they run inside the Docker network and must use the
# internal hostname.
public_client = Minio(
    _settings.minio_public_endpoint,
    access_key=_settings.minio_access_key,
    secret_key=_settings.minio_secret_key,
    secure=_settings.minio_secure,
)


def ensure_buckets() -> None:
    for bucket in [b.strip() for b in _settings.default_buckets.split(",") if b.strip()]:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
