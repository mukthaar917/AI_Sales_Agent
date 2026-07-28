from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_name: str = "AI Sales Agent"
    app_env: str = "development"
    debug: bool = True

    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    database_url: str
    redis_url: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()