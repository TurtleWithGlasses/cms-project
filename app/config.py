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

    # CORS settings
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()