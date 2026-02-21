from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    # Application settings
    app_name: str = "CMS Project"
    app_version: str = "1.17.0"
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
    redis_password: str | None = None
    redis_url: str | None = None
    session_expire_seconds: int = 3600  # 1 hour

    # CORS settings
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Email/SMTP settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "noreply@cms-project.com"
    app_url: str = "http://localhost:8000"

    # Media settings
    media_max_file_size: int = 10485760  # 10MB
    media_jpeg_quality: int = 85
    media_png_compression: int = 6
    media_enable_exif_strip: bool = True

    # Search settings
    search_min_query_length: int = 2
    search_max_query_length: int = 200
    search_default_limit: int = 20
    search_max_limit: int = 100
    search_highlight_max_words: int = 35
    search_highlight_min_words: int = 15
    search_suggestions_limit: int = 10
    search_analytics_enabled: bool = True
    search_language: str = "english"

    # Comment settings
    comment_report_auto_flag_threshold: int = 3

    # Performance settings
    slow_query_threshold_ms: int = 100
    gzip_minimum_size: int = 500
    etag_enabled: bool = True

    # Monitoring settings
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0.1  # 10% of transactions
    sentry_profiles_sample_rate: float = 0.1  # 10% of profiled transactions

    # OpenTelemetry distributed tracing
    otel_exporter_endpoint: str | None = None  # e.g. "http://jaeger:4317" (OTLP/gRPC)
    otel_service_name: str = "cms-api"

    # Social Media
    twitter_handle: str | None = None  # e.g. "@mycms" for OG/TC tags
    twitter_bearer_token: str | None = None  # For auto-post (stub — not called unless set)
    facebook_app_id: str | None = None  # For OG fb:app_id tag
    linkedin_company_id: str | None = None  # For share URLs

    # Analytics
    google_analytics_measurement_id: str | None = None  # GA4 format: G-XXXXXXXXXX
    google_analytics_api_secret: str | None = None  # GA4 Measurement Protocol API secret
    plausible_domain: str | None = None  # e.g. "mycms.example.com"
    plausible_api_url: str = "https://plausible.io"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")


settings = Settings()
