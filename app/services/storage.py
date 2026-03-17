from pathlib import Path
import shutil

import boto3

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

    def upload_generated_audio(self, local_path: str, key: str) -> str:
        try:
            self.client.upload_file(local_path, settings.s3_bucket, key)
            return f"s3://{settings.s3_bucket}/{key}"
        except Exception:
            return f"file://{local_path}"

    def publish_local_media(self, source_path: str, user_id: str, track_id: str) -> str:
        media_root = Path("app/media/generated") / user_id
        media_root.mkdir(parents=True, exist_ok=True)
        destination = media_root / f"{track_id}.wav"
        shutil.copy2(source_path, destination)
        return f"/media/generated/{user_id}/{track_id}.wav"
            # Local fallback if MinIO/S3 is unavailable.
            return f"file://{local_path}"
        self.client.upload_file(local_path, settings.s3_bucket, key)
        return f"s3://{settings.s3_bucket}/{key}"
