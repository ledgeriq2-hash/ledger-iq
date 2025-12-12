from __future__ import annotations

import importlib
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import init_logging
from app.core.soft_launch import refresh_soft_launch_slugs
from app.core.redis import get_redis
from app.metrics import setup_metrics
from app.middleware import register_middlewares

settings = get_settings()
logger = logging.getLogger(__name__)


def _load_api_router() -> APIRouter:
    module = importlib.import_module("app.api.router")
    router = getattr(module, "router", None)
    if router is None:
        logger.warning("No router found in app.api.router; using empty router")
        return APIRouter()
    if not isinstance(router, APIRouter):
        raise TypeError("app.api.router.router must be an APIRouter instance")
    return router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_logging(settings.debug)
    app.state.settings = settings

    redis_client = None
    try:
        redis_client = await get_redis()
        await redis_client.ping()
    except Exception as exc:  # pragma: no cover - startup guard
        logger.warning("Redis warmup failed: %s", exc)
    try:
        await refresh_soft_launch_slugs()
    except Exception as exc:  # pragma: no cover - startup guard
        logger.warning("Soft launch cache warmup failed: %s", exc)
    try:
        yield
    finally:
        if redis_client:
            await redis_client.close()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

setup_metrics(app)
register_middlewares(app)
register_exception_handlers(app)


if settings.backend_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

api_router = _load_api_router()
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


__all__ = ["app"]
