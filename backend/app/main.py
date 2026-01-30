from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv


def _load_local_env_files() -> None:
    """
    Load local `.env*` files for development convenience.

    Production should rely on process environment variables only.
    """
    explicit_env = (os.getenv("ENVIRONMENT") or "").strip().lower()
    if explicit_env in {"production", "prod"}:
        return

    repo_root = Path(__file__).resolve().parents[2]
    backend_dir = Path(__file__).resolve().parents[1]

    for candidate in (backend_dir / ".env", repo_root / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)

    env = (os.getenv("ENVIRONMENT") or "").strip().lower()
    if not env:
        for candidate in (backend_dir / ".env.development", repo_root / ".env.development"):
            if candidate.exists():
                load_dotenv(candidate, override=False)
        env = (os.getenv("ENVIRONMENT") or "").strip().lower()

    if env and env not in {"production", "prod"}:
        for candidate in (backend_dir / f".env.{env}", repo_root / f".env.{env}"):
            if candidate.exists():
                load_dotenv(candidate, override=False)


_load_local_env_files()

import importlib
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import init_logging
from app.core.redis import get_redis
from app.core.soft_launch import refresh_soft_launch_slugs
from app.database import async_session_maker
from app.metrics import setup_metrics
from app.middleware import register_middlewares
from app.shared.errors import ErrorEnvelope, ErrorObject, ErrorResponse
from app.core.exceptions import json_error_response


settings = get_settings()
logger = logging.getLogger(__name__)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
DEV_AI_CSRF_BYPASS_PREFIX = "/api/v1/ai/"
DEV_ML_CSRF_BYPASS_PREFIXES = (
    "/api/v1/ml/predictions/ingest",
    "/api/v1/ml/snapshots",
)
DB_HEALTH_TIMEOUT_SECONDS = 2.0
REDIS_HEALTH_TIMEOUT_SECONDS = 2.0


class CSRFMiddleware(BaseHTTPMiddleware):
    """Simple double-submit cookie CSRF protection."""

    def __init__(self, app: FastAPI, settings):
        super().__init__(app)
        self.settings = settings
        self.exempt_paths = {path.lower() for path in getattr(settings, "csrf_exempt_paths", [])}

    def _is_exempt(self, path: str) -> bool:
        lower_path = path.lower()
        return lower_path in self.exempt_paths

    def _is_dev_runtime(self) -> bool:
        env = str(getattr(self.settings, "environment", "production") or "production").strip().lower()
        if env in {"production", "prod"}:
            return False
        if bool(getattr(self.settings, "debug", False)):
            return True
        return env in {"development", "dev", "local", "test"}

    def _should_bypass_for_dev_ai(self, request: Request) -> bool:
        if not self._is_dev_runtime():
            return False
        lower_path = (request.url.path or "").lower()
        return lower_path == DEV_AI_CSRF_BYPASS_PREFIX.rstrip("/") or lower_path.startswith(DEV_AI_CSRF_BYPASS_PREFIX)

    def _should_bypass_for_dev_ml(self, request: Request) -> bool:
        if not self._is_dev_runtime():
            return False
        lower_path = (request.url.path or "").lower()
        return any(lower_path.startswith(prefix) for prefix in DEV_ML_CSRF_BYPASS_PREFIXES)

    async def dispatch(self, request: Request, call_next):
        if not self.settings.csrf_enabled:
            return await call_next(request)
        if request.method.upper() in SAFE_METHODS:
            return await call_next(request)

        if self._is_exempt(request.url.path):
            return await call_next(request)

        if self._should_bypass_for_dev_ai(request):
            logger.debug(
                "csrf.bypass.dev_ai",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "reason": "dev_runtime_ai_prefix",
                },
            )
            return await call_next(request)

        if self._should_bypass_for_dev_ml(request):
            logger.debug(
                "csrf.bypass.dev_ml_ingest",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "reason": "dev_runtime_ml_ingest",
                },
            )
            return await call_next(request)

        csrf_cookie = request.cookies.get(self.settings.csrf_cookie_name)
        csrf_header = request.headers.get(self.settings.csrf_header_name)
        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            return json_error_response(status.HTTP_403_FORBIDDEN, "csrf_failed", "CSRF validation failed")

        return await call_next(request)


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
    init_logging(settings.debug, settings.log_level)
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
    version=getattr(settings, "app_version", "0.0.0"),
    debug=settings.debug,
    lifespan=lifespan,
    generate_unique_id_function=lambda route: f"{sorted(getattr(route, 'methods', {'GET'}))[0].lower()}_{getattr(route, 'path_format', '').lstrip('/').replace('/', '_').replace('-', '_').replace('{', '').replace('}', '')}",
)

app.add_middleware(CSRFMiddleware, settings=settings)
setup_metrics(app)
register_middlewares(app, settings)
register_exception_handlers(app)

def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=getattr(settings, "app_version", "0.0.0"),
        routes=app.routes,
        description=getattr(app, "description", None),
    )
    components = schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes.setdefault(
        "BearerAuth",
        {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
    )
    schemas["ErrorObject"] = ErrorObject.model_json_schema(ref_template="#/components/schemas/{model}")
    schemas["ErrorEnvelope"] = ErrorEnvelope.model_json_schema(ref_template="#/components/schemas/{model}")
    schemas["ErrorResponse"] = ErrorResponse.model_json_schema(ref_template="#/components/schemas/{model}")

    error_ref = {"$ref": "#/components/schemas/ErrorEnvelope"}
    error_content = {"application/json": {"schema": error_ref}}
    error_headers = {"X-Request-ID": {"schema": {"type": "string"}}}
    for path_item in (schema.get("paths") or {}).values():
        if not isinstance(path_item, dict):
            continue
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.setdefault("responses", {})
            for status_code in ("400", "401", "403", "404", "409", "422", "500"):
                responses[status_code] = {
                    "description": "Error",
                    "content": error_content,
                    "headers": error_headers,
                }

    health_headers = {"X-Request-ID": {"schema": {"type": "string"}}}
    healthz = schema.get("paths", {}).get("/healthz", {}).get("get")
    if isinstance(healthz, dict):
        responses = healthz.setdefault("responses", {})
        responses.setdefault("200", {}).setdefault("headers", health_headers)
        healthz.setdefault("summary", "Health check")
        healthz.setdefault("tags", ["health"])

    readyz = schema.get("paths", {}).get("/readyz", {}).get("get")
    if isinstance(readyz, dict):
        responses = readyz.setdefault("responses", {})
        responses.setdefault("200", {}).setdefault("headers", health_headers)
        responses.setdefault("503", {"description": "Service unavailable", "content": error_content, "headers": error_headers})
        readyz.setdefault("summary", "Readiness check")
        readyz.setdefault("tags", ["health"])

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = _custom_openapi  # type: ignore[assignment]


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


async def _db_check(log_label: str) -> bool:
    try:
        async with async_session_maker() as session:
            await asyncio.wait_for(
                session.execute(text("SELECT 1")),
                timeout=DB_HEALTH_TIMEOUT_SECONDS,
            )
    except asyncio.TimeoutError:  # pragma: no cover - defensive guard
        logger.warning(log_label, extra={"reason": "timeout"})
        return False
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.warning(log_label, extra={"reason": str(exc)})
        return False
    return True


async def _redis_check(log_label: str) -> bool:
    try:
        client = await get_redis()
        if hasattr(client, "ping"):
            await asyncio.wait_for(
                client.ping(),
                timeout=REDIS_HEALTH_TIMEOUT_SECONDS,
            )
    except asyncio.TimeoutError:  # pragma: no cover - defensive guard
        logger.warning(log_label, extra={"reason": "timeout"})
        return False
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.warning(log_label, extra={"reason": str(exc)})
        return False
    return True


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/healthz", tags=["health"], summary="Health check")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/live", tags=["health"])
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def health_ready():
    if not await _db_check("readiness.failed"):
        return json_error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "service_unavailable",
            "Service not ready",
            {"postgres": False},
        )
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
async def health_db():
    if not await _db_check("health.db.failed"):
        return json_error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "service_unavailable",
            "Database not ready",
            {"postgres": False},
        )
    return {"status": "ok"}


@app.get("/readyz", tags=["health"], summary="Readiness check")
async def readyz():
    postgres_ready = await _db_check("readyz.postgres.failed")
    redis_ready = await _redis_check("readyz.redis.failed")
    if not postgres_ready or not redis_ready:
        return json_error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "service_unavailable",
            "Service not ready",
            {"postgres": postgres_ready, "redis": redis_ready},
        )
    return {"status": "ok"}


__all__ = ["app"]
