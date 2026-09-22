"""Application configuration loaded from environment variables.

Uses pydantic-settings to validate and type-check all config at startup.
Missing required vars will raise a clear error before the app starts.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env file and environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://localhost:5432/vikas"
    # Separate test DB URL — used by pytest; defaults to main DB if not set
    database_url_test: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # JWT Authentication
    jwt_secret: str = "CHANGE-ME"  # Must be overridden in production
    jwt_secret_fallback: str = ""  # Used during zero-downtime key rotation
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7  # Refresh token validity period

    # External APIs & Quotas
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    jooble_api_key: str = ""
    adzuna_monthly_budget: int = 1000
    adzuna_warning_threshold: float = 0.8

    # Pipeline Thresholds & Governance
    min_confidence_threshold: float = 0.75
    high_volume_threshold: int = 50
    academic_veto_enabled: bool = False

    # Groq LLM — used ONLY for alert text, trainee chat, employer free-text parsing
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    chat_rate_limit_per_minute: int = 10

    # Environment: development, test, staging, production
    environment: str = "development"

    # CORS
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list.

        Strictly forbids wildcard '*' in production mode.
        """
        origins = [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]
        if self.environment == "production" and ("*" in origins or not origins):
            raise ValueError(
                "Wildcard '*' or empty CORS origins is strictly forbidden in production. "
                "Specify explicit production domains (e.g. 'https://vikas.gov.in')."
            )
        return origins


# Singleton instance — import this throughout the app
settings = Settings()
