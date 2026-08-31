from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

CONFIG_FILE = Path(__file__).resolve()

# config.py -> core -> app -> api root
API_ROOT = CONFIG_FILE.parents[2]

# Local project:
# D:\AI_Sales_Agent\apps\api -> D:\AI_Sales_Agent
#
# Railway:
# Usually /app is the deployed backend root.
if len(API_ROOT.parents) > 1:
    PROJECT_ROOT = API_ROOT.parents[1]
else:
    PROJECT_ROOT = API_ROOT

# Local .env support.
# Railway reads environment variables directly, so the file does not
# need to exist there.
ENV_FILE = PROJECT_ROOT / ".env"

if not ENV_FILE.exists():
    ENV_FILE = API_ROOT / ".env"


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

    # Redis is optional for the Railway demo.
    # If REDIS_URL is not configured, the application can still start.
    redis_url: str = ""

    # ------------------------------------------------------------------
    # Frontend
    # ------------------------------------------------------------------
    frontend_url: str = "http://localhost:3000"

    # ------------------------------------------------------------------
    # Knowledge Base
    # ------------------------------------------------------------------
    knowledge_storage_dir: str = str(
        PROJECT_ROOT / "storage" / "documents"
    )

    knowledge_max_upload_bytes: int = 10 * 1024 * 1024

    # ------------------------------------------------------------------
    # AI Provider
    # ------------------------------------------------------------------
    ai_provider: str = "openai"
    ai_model: str = "gpt-4.1-mini"
    ai_api_key: str = ""
    ai_timeout_seconds: float = 30.0
    ai_max_output_tokens: int = 1200

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