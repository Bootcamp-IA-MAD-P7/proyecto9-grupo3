"""Assemble the application; run with uvicorn app.main:create_app --factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.auth.repository import AuthRepository
from app.auth.router import router as auth_router
from app.auth.service import AuthService
from app.config import Settings
from app.comments.repository import CommentError, CommentRepository
from app.comments.router import router as comments_router
from app.comments.service import CommentService
from app.comments.scoring import SimulatedScorer
from app.database import Database
from app.errors import validation_error
from app.health import router as health_router


def create_app() -> FastAPI:
    settings = Settings()
    database = Database(settings.database_path)
    scorer = SimulatedScorer()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.initialize()
        yield

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Foundation for human-assisted comment moderation.",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.database = database
    app.state.auth_service = AuthService(AuthRepository(database), settings)
    app.state.comment_service = CommentService(CommentRepository(database), scorer)
    app.add_exception_handler(RequestValidationError, validation_error)

    async def comment_error(request: Request, error: CommentError) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content={"detail": error.detail})

    app.add_exception_handler(CommentError, comment_error)

    @app.middleware("http")
    async def prevent_auth_caching(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/auth/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        if request.url.path.startswith("/comments"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        return response

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(comments_router)
    return app
