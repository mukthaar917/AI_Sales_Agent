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
# /app -> keep /app because there are not enough parent levels.
if len(API_ROOT.parents) > 1:
    PROJECT_ROOT = API_ROOT.parents[1]
else:
    PROJECT_ROOT = API_ROOT

# Locally this resolves to:
# D:\AI_Sales_Agent\.env
#
# On Railway there normally is no .env file; Railway environment
# variables are read directly by BaseSettings.
ENV_FILE = PROJECT_ROOT / ".env"

if not ENV_FILE.exists():
    ENV_FILE = API_ROOT / ".env"


class Settings(BaseSettings):
    app_name: str = "AI Sales Agent"
    app_env: str = "development"
    debug: bool = True

    database_url: str
    redis_url: str
    frontend_url: str = "http://localhost:3000"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()