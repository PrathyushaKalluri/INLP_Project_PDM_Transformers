import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ENV: str = "development"

    # CORS
    # Comma-separated list, e.g. "https://app.example.com,https://preview.example.com"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Allow Vercel preview/prod domains by default; tighten if needed.
    CORS_ORIGIN_REGEX: str = r"^https://.*\.vercel\.app$"

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
    NLP_PIPELINE_PATH: str = "pipeline"  # Path to NLP pipeline directory
    NLP_SERVICE_BASE_URL: str = "http://localhost:8001"
    NLP_SERVICE_TIMEOUT_SECONDS: int = 300
    NLP_SERVICE_POLL_INTERVAL_SECONDS: int = 2
    NLP_SERVICE_MAX_POLL_SECONDS: int = 300

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
