from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[4]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    app_name: str = "AI Sales Agent"
    app_env: str = "development"
    debug: bool = True

    # ------------------------------------------------------------------
    # Database & Redis
    # ------------------------------------------------------------------
    database_url: str
    test_database_url: str = ""
    redis_url: str

    # ------------------------------------------------------------------
    # Frontend
    # ------------------------------------------------------------------
    frontend_url: str = "http://localhost:3000"

    # ------------------------------------------------------------------
    # Gmail OAuth
    # ------------------------------------------------------------------
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = (
        "http://localhost:8000/api/v1/gmail/oauth/callback"
    )

    gmail_scopes: str = (
        "https://www.googleapis.com/auth/gmail.readonly"
    )

    # ------------------------------------------------------------------
    # Token Encryption
    # ------------------------------------------------------------------
    token_encryption_key: str = ""

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # ------------------------------------------------------------------
    # Pydantic Settings
    # ------------------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()