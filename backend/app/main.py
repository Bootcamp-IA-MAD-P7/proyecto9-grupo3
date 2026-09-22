"""Assemble the application; run with uvicorn app.main:create_app --factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.auth.repository import AuthRepository
from app.auth.router import router as auth_router
from app.auth.service import AuthService
from app.comments.repository import CommentRepository
from app.comments.router import router as comments_router
from app.comments.scoring import select_scorer
from app.comments.service import CommentService
from app.config import Settings
from app.database import Database
from app.errors import validation_error
from app.health import router as health_router


def create_app() -> FastAPI:
    settings = Settings()
    database = Database(settings.database_url or settings.database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.initialize()
        moderator_password = settings.demo_moderator_password
        supervisor_password = settings.demo_supervisor_password
        if bool(moderator_password) != bool(supervisor_password):
            raise RuntimeError("Both demo user passwords must be configured together")
        if moderator_password and supervisor_password:
            from app.seed_demo_users import seed_demo_users

            seed_demo_users(
                database,
                moderator_password.get_secret_value(),
                supervisor_password.get_secret_value(),
            )
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
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )
    app.state.database = database
    app.state.auth_service = AuthService(AuthRepository(database), settings)
    app.state.comment_service = CommentService(CommentRepository(database), select_scorer(settings))
    app.add_exception_handler(RequestValidationError, validation_error)

    @app.middleware("http")
    async def prevent_auth_caching(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(("/auth/", "/comments")):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        return response

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(comments_router)
    return app


# Supported FastAPI entrypoint for Vercel Services. Tests and local tooling can
# continue to call create_app() for an isolated application instance.
app = create_app()
