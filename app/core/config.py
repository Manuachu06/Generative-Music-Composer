from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Generative Music Composer API"
    environment: str = "dev"

    redis_url: str = "redis://localhost:6379/0"
    s3_bucket: str = "bgm-assets"
    s3_endpoint_url: str = "http://localhost:9000"
    aws_access_key_id: str = "minio"
    aws_secret_access_key: str = "minio123"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
