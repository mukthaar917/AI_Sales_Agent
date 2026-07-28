from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "AI Sales Agent API is running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "application": settings.app_name,
        "environment": settings.app_env,
    }

app.include_router(api_router, prefix="/api/v1")