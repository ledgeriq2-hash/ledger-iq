import asyncio
import gc
import logging
import os
import sys
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import types
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.engine import make_url

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("FRONTEND_URL", "http://testserver")
os.environ.setdefault("CSRF_ENABLED", "false")
os.environ.setdefault("FEATURE_OPTIONAL_ROUTES", "true")

from app.database import Base, async_session_maker, dispose_engine, engine  # noqa: E402
import app.models  # noqa: E402
from app.main import app  # noqa: E402
import app.core.redis as redis_module  # noqa: E402
from app.services import email_service  # noqa: E402
from app.core.security import create_access_token, decode_token  # noqa: E402
from app.schemas.tenant import TenantPublic  # noqa: E402
from app.schemas.user import UserPublic  # noqa: E402
from app.services import tenant_service, user_service  # noqa: E402

logger = logging.getLogger(__name__)


class DummyRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.closed = False

    async def ping(self) -> bool:  # pragma: no cover - simple stub
        return True

    async def close(self) -> None:
        self.closed = True

    async def set(self, key: str, value, ex: int | None = None) -> bool:
        self.store[key] = str(value)
        return True

    async def get(self, key: str):
        return self.store.get(key)

    async def getdel(self, key: str):
        return self.store.pop(key, None)

    async def delete(self, key: str) -> int:
        return int(self.store.pop(key, None) is not None)

    async def exists(self, key: str) -> int:
        return int(key in self.store)

    async def incr(self, key: str) -> int:
        value = int(self.store.get(key, 0)) + 1
        self.store[key] = str(value)
        return value

    async def expire(self, key: str, seconds: int) -> bool:  # pragma: no cover - simple stub
        return True

# Allow JSONB on SQLite for tests
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"

# Fallback for UUID default for SQLite
@compiles(types.UUID, "sqlite")
def compile_uuid_sqlite(element, compiler, **kw):
    return "CHAR(36)"


def _strip_server_defaults_for_sqlite():
    """SQLite does not support server-side uuid_generate_v4(); drop those defaults for tests."""
    for table in Base.metadata.tables.values():
        for column in table.columns:
            sd = getattr(column, "server_default", None)
            if sd is not None:
                arg_str = str(getattr(sd, "arg", ""))
                if "uuid_generate_v4" in arg_str.lower():
                    column.server_default = None


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.run_until_complete(asyncio.sleep(0))
    loop.close()
    asyncio.set_event_loop(None)


@pytest.fixture(autouse=True)
def _ensure_loop_after_test(event_loop):
    yield
    if event_loop.is_closed():
        return
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(event_loop)
    gc.collect()


@pytest.fixture(scope="session", autouse=True)
def setup_db(event_loop):
    # Patch redis with in-memory dummy to avoid external dependency during tests
    dummy = DummyRedis()
    redis_module._redis_client = dummy

    async def _get_dummy():
        return dummy

    redis_module.get_redis = _get_dummy

    # Patch email sending to a no-op for tests
    async def _send_email_stub(*args, **kwargs):
        return None

    email_service.send_email = _send_email_stub

    def _run(coro) -> None:
        event_loop.run_until_complete(coro)

    async def _setup() -> None:
        _strip_server_defaults_for_sqlite()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _teardown() -> None:
        url = make_url(os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./test.db"))
        is_sqlite = url.drivername.startswith("sqlite")
        async with engine.begin() as conn:
            if is_sqlite:
                await conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
                await conn.run_sync(_drop_all_tables)
                await conn.exec_driver_sql("PRAGMA foreign_keys=ON")
            else:
                await conn.run_sync(Base.metadata.drop_all)
        await dispose_engine()
        await asyncio.sleep(0)
        if url.drivername.startswith("sqlite") and url.database:
            db_path = Path(url.database)
            if db_path.exists():
                for _ in range(5):
                    try:
                        db_path.unlink()
                        break
                    except PermissionError:
                        await asyncio.sleep(0.1)

    def _drop_all_tables(sync_conn) -> None:
        for table in Base.metadata.tables.values():
            table.drop(sync_conn, checkfirst=True)

    _run(_setup())
    yield
    _run(_teardown())


@pytest.fixture
async def client():
    transport = ASGITransport(app=app, raise_app_exceptions=False)

    async def _ensure_tenant_headers(request):
        path = (request.url.path or "").lower()
        if not path.startswith("/api/"):
            return
        if path.startswith("/api/v1/auth/login"):
            return

        if "X-Tenant-Id" in request.headers:
            return

        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()

        if token:
            try:
                payload = decode_token(token)
                tenant_id = payload.get("tenant_id")
                actor_id = payload.get("sub")
                if tenant_id:
                    request.headers["X-Tenant-Id"] = str(tenant_id)
                if actor_id:
                    request.headers["X-Actor-Id"] = str(actor_id)
                return
            except Exception:
                # Fall through to dummy tenant header for endpoints where auth isn't required.
                pass

        request.headers["X-Tenant-Id"] = str(uuid.uuid4())

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        event_hooks={"request": [_ensure_tenant_headers]},
    ) as ac:
        yield ac


@pytest.fixture
def register_owner(client: AsyncClient):
    async def _register(slug: str | None = None, email: str | None = None, password: str = "Secret123!"):
        tenant_slug = slug or f"tenant-{uuid.uuid4().hex[:6]}"
        tenant_email = email or f"{tenant_slug}@example.com"
        payload = {
            "tenant": {"name": f"Tenant {tenant_slug}", "slug": tenant_slug},
            "admin": {"email": tenant_email, "password": password, "full_name": "Owner"},
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        if response.status_code == 201:
            return response.json()
        if response.status_code != 404:
            assert response.status_code == 201, response.text

        logger.warning(
            "tests.auth.register_fallback",
            extra={"reason": "auth_register_not_found"},
        )
        async with async_session_maker() as session:
            tenant = await tenant_service.create_tenant(session, payload["tenant"], scope_id=None)
            user = await user_service.create_user(
                session,
                tenant.id,
                {
                    "email": tenant_email,
                    "password": password,
                    "full_name": payload["admin"]["full_name"],
                    "is_superuser": True,
                },
            )

        access_token = create_access_token(
            str(user.id),
            claims={"tenant_id": str(tenant.id), "token_version": 0},
        )
        return {
            "tenant": TenantPublic.model_validate(tenant).model_dump(mode="json"),
            "user": UserPublic.model_validate(user).model_dump(mode="json"),
            "tokens": {"access_token": access_token, "token_type": "bearer"},
            "soft_launch_badge": None,
        }

    return _register
