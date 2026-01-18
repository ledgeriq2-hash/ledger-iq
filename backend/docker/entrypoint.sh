#!/usr/bin/env bash
set -euo pipefail

DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${POSTGRES_USER:-ledgeriq}"
DB_NAME="${POSTGRES_DB:-ledgeriq}"
export PGPASSWORD="${POSTGRES_PASSWORD:-}"
export PYTHONPATH="/app:${PYTHONPATH:-}"

# Prefer a sync driver for Alembic to avoid asyncpg greenlet issues
if [ -z "${ALEMBIC_DATABASE_URL:-}" ] && [ -n "${DATABASE_URL:-}" ]; then
  export ALEMBIC_DATABASE_URL="${DATABASE_URL/postgresql+asyncpg/postgresql+psycopg}"
fi

cd /app

echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
until pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; do
  sleep 2
done

echo "Running pending migrations..."
alembic upgrade head

echo "Starting gunicorn..."
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:8000 \
  --workers 2 \
  --timeout 120
