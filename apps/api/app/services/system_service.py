from redis import Redis
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine


def check_database() -> str:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "disconnected"


def check_redis() -> str:
    try:
        client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        client.ping()
        return "connected"
    except Exception:
        return "disconnected"


def get_system_status() -> dict[str, str]:
    return {
        "api": "connected",
        "database": check_database(),
        "redis": check_redis(),
    }