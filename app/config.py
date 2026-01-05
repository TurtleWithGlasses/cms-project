from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class Settings(BaseSettings):
    # Application settings
    app_name: str = "CMS Project"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # Database settings
    database_url: str

    # Security settings
    secret_key: str
    access_token_expire_minutes: int = 30

    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_url: Optional[str] = None
    session_expire_seconds: int = 3600  # 1 hour

    # CORS settings
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()