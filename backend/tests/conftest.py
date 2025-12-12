import os
import sys
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import types
from sqlalchemy.ext.compiler import compiles

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("FRONTEND_URL", "http://testserver")

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
import app.core.redis as redis_module  # noqa: E402
from app.services import email_service  # noqa: E402


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


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
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

    _strip_server_defaults_for_sqlite()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    db_path = Path("./test.db")
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
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
        assert response.status_code == 201, response.text
        return response.json()

    return _register
