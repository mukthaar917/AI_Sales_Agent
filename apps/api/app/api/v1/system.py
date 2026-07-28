from fastapi import APIRouter

from app.services.system_service import get_system_status


router = APIRouter()


@router.get("/status")
def get_system_status_endpoint() -> dict[str, str]:
    return get_system_status()