from __future__ import annotations

from pathlib import Path

import boto3

from app.core.config import settings


class StorageService:
    """Optional external storage publisher.

    The default product behavior is ephemeral output only; generated music is not
    stored locally by the app after the request completes.
    """

    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

    def upload_generated_audio(self, local_path: str, key: str) -> str | None:
        try:
            self.client.upload_file(local_path, settings.s3_bucket, key)
            return f"s3://{settings.s3_bucket}/{key}"
        except Exception:
            return None

    def cleanup_temp_file(self, local_path: str) -> None:
        try:
            Path(local_path).unlink(missing_ok=True)
        except Exception:
            return None
