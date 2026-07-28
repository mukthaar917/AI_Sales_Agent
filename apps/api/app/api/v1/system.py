from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def get_system_status() -> dict[str, str]:
    return {
        "api": "connected",
        "database": "not_checked",
        "redis": "not_checked",
    }