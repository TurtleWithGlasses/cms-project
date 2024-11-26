from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "CMS API"
    app_version: str = "1.0.0"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://cms_admin:mehmetcms@localhost/cms_project"
    secret_key: str = "default_secret_key_for_dev"

    access_token_expire_minutes: int = 30
    environment: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()