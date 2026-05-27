"""Rawasi Pricing Intelligence FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import __version__
from api.core.config import get_settings
from api.core.errors import (
    AllocationError,
    ClaudeExtractionError,
    InsufficientDataError,
    NormalizationError,
    NotFoundError,
    RawasiError,
    ValidationError,
)
from api.core.logging import configure_logging, get_logger
from api.routers import (
    analytics,
    boq_import,
    health,
    master_items,
    normalization,
    tenders,
)

LOG = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    LOG.info(
        "app_starting",
        env=settings.app_env,
        version=__version__,
    )
    yield
    LOG.info("app_stopping")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Rawasi Pricing Intelligence",
        version=__version__,
        description=(
            "Intelligent pricing system for Saudi government tenders. "
            "Engines: reference pricing, Go/No-Go, competitor profiling, win probability."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(tenders.router)
    app.include_router(boq_import.router)
    app.include_router(master_items.router)
    app.include_router(normalization.router)
    app.include_router(analytics.router)

    register_exception_handlers(app)
    return app


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValidationError)
    async def _validation(req: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(NotFoundError)
    async def _not_found(req: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InsufficientDataError)
    async def _insufficient(req: Request, exc: InsufficientDataError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(NormalizationError)
    async def _normalization(req: Request, exc: NormalizationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(AllocationError)
    async def _allocation(req: Request, exc: AllocationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ClaudeExtractionError)
    async def _claude(req: Request, exc: ClaudeExtractionError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(RawasiError)
    async def _rawasi(req: Request, exc: RawasiError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc)})


app = create_app()
