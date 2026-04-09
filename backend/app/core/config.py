import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ENV: str = "development"

    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "meeting_tasks"

    # JWT
    SECRET_KEY: str = "change-this-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # File Upload
    UPLOAD_DIR: str = "uploads/transcripts"
    MAX_UPLOAD_SIZE_MB: int = 10

    # NLP
    NLP_MODE: str = "local"
    NLP_PIPELINE_PATH: str = "../meeting-action-extractor/src"
    NLP_SERVICE_BASE_URL: str = "http://localhost:8001"
    NLP_SERVICE_TIMEOUT_SECONDS: int = 30
    NLP_SERVICE_POLL_INTERVAL_SECONDS: int = 2
    NLP_SERVICE_MAX_POLL_SECONDS: int = 300

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
