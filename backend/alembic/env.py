from __future__ import annotations

import os
import logging
from logging.config import fileConfig
import importlib
import pkgutil
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None

from alembic import context
from sqlalchemy import engine_from_config, text
from sqlalchemy import pool
from sqlalchemy.engine.url import make_url

LOADED_ENV_FILES: list[Path] = []
_DEBUG_ENV_PRINTED = False


def _parse_env_file(path: Path) -> bool:
    loaded = False
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, _, value = raw.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)
            loaded = True
    return loaded


def _load_env_file(path: Path) -> bool:
    if load_dotenv is not None:
        return bool(load_dotenv(path, override=False))
    return _parse_env_file(path)


# IMPORTANT: load env BEFORE importing app.* (settings are evaluated at import time)
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

    def load_candidates(paths: list[Path]) -> None:
        for path in paths:
            if path.exists() and _load_env_file(path):
                LOADED_ENV_FILES.append(path)

    load_candidates([backend_dir / ".env.local", repo_root / ".env.local"])

    env = (os.getenv("ENVIRONMENT") or "development").strip().lower()
    if env and env not in {"production", "prod"}:
        load_candidates([backend_dir / f".env.{env}", repo_root / f".env.{env}"])


_load_local_env_files()

from app.config import get_settings  # noqa: E402
from app.database import Base  # noqa: E402
import app.models  # noqa: F401,E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()


def _import_all_models() -> None:
    """Ensure all model modules are imported so metadata is populated."""
    package = app.models
    for module_info in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        importlib.import_module(module_info.name)


def _get_alembic_database_url() -> str:
    """
    Resolve a sync-safe database URL for migrations.

    Prefer ALEMBIC_DATABASE_URL or DATABASE_URL_SYNC, otherwise derive a
    psycopg-powered URL from the application DATABASE_URL (which may be asyncpg).
    """
    explicit = os.getenv("ALEMBIC_DATABASE_URL") or os.getenv("DATABASE_URL_SYNC")
    if explicit:
        url = make_url(explicit)
        _maybe_debug_env(url)
        return url.render_as_string(hide_password=False)

    base_url = settings.database_url
    if not base_url:
        raise ValueError("DATABASE_URL is not configured; migrations cannot run.")

    url = make_url(base_url)
    if url.drivername.startswith("postgresql+asyncpg"):
        url = url.set(drivername="postgresql+psycopg")
    elif url.drivername == "postgresql+psycopg2":
        url = url.set(drivername="postgresql+psycopg")
    _maybe_debug_env(url)
    return url.render_as_string(hide_password=False)


def _maybe_debug_env(url) -> None:
    if os.getenv("ALEMBIC_DEBUG_ENV") != "1":
        return
    global _DEBUG_ENV_PRINTED
    if _DEBUG_ENV_PRINTED:
        return
    _DEBUG_ENV_PRINTED = True
    loaded = ", ".join(str(path) for path in LOADED_ENV_FILES) if LOADED_ENV_FILES else "<none>"
    host = url.host or ""
    if not host and url.database:
        host = url.database
    print(f"Alembic env files loaded: {loaded}")
    print(f"Alembic DB host: {host or 'unknown'}")


_import_all_models()
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = _get_alembic_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        try:
            if connection.dialect.name == "postgresql":
                connection.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        except Exception:
            # Extension creation is best-effort (e.g. reduced permissions), migrations may still succeed.
            pass

        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_alembic_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
