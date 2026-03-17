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
        self.client.upload_file(local_path, settings.s3_bucket, key)
        return f"s3://{settings.s3_bucket}/{key}"
