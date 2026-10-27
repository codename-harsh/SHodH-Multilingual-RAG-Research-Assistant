"""Upload storage shared by the API and Celery worker.

Local development uses a shared filesystem path. Hosted deployments can use an
S3-compatible bucket so the API and worker do not need a shared disk.
"""

import tempfile
from pathlib import Path

from app.core.config import get_settings


def _s3_client():
    import boto3

    settings = get_settings()
    if not settings.s3_bucket or not settings.s3_access_key_id or not settings.s3_secret_access_key:
        raise RuntimeError("S3 upload storage requires bucket and access credentials")
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url or None,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )


def is_s3_reference(reference: str) -> bool:
    return reference.startswith("s3://")


def upload_pdf(local_path: Path, object_key: str) -> str:
    settings = get_settings()
    if settings.upload_storage_backend.lower() != "s3":
        return str(local_path)
    _s3_client().upload_file(str(local_path), settings.s3_bucket, object_key)
    return f"s3://{settings.s3_bucket}/{object_key}"


def materialize_pdf(reference: str) -> tuple[Path, bool]:
    """Return a local path and whether the caller must remove that temp file."""
    if not is_s3_reference(reference):
        return Path(reference), False
    bucket_and_key = reference[5:]
    bucket, separator, key = bucket_and_key.partition("/")
    if not separator or not bucket or not key:
        raise ValueError("Invalid S3 upload reference")
    temporary = tempfile.NamedTemporaryFile(prefix="shodh-", suffix=".pdf", delete=False)
    temporary.close()
    path = Path(temporary.name)
    try:
        _s3_client().download_file(bucket, key, str(path))
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path, True


def delete_upload(reference: str) -> None:
    if is_s3_reference(reference):
        bucket_and_key = reference[5:]
        bucket, separator, key = bucket_and_key.partition("/")
        if separator and bucket and key:
            _s3_client().delete_object(Bucket=bucket, Key=key)
        return
    Path(reference).unlink(missing_ok=True)
