"""Assemble the application; run with uvicorn app.main:create_app --factory."""

from fastapi import FastAPI

from app.config import Settings
from app.health import router as health_router


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Foundation for human-assisted comment moderation.",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    app.include_router(health_router)
    return app
