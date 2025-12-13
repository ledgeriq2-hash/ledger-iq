# Ledger IQ Backend

Backend stack: FastAPI, SQLAlchemy async, Alembic, Celery, Redis, PostgreSQL.

## Quick start (Docker)
1) Copy env templates: `cp .env.example .env` and `cp backend/.env.example backend/.env` (edit secrets).
2) Build and start: `docker-compose up --build`.
3) API: http://localhost:8000/health

## Services
- backend: FastAPI app (`uvicorn app.main:app`)
- db: PostgreSQL 15
- redis: cache/broker
- worker: Celery worker
- beat: Celery beat (scheduled tasks)

## Redis (local)
- Start Redis: `docker-compose up redis` (already included in `docker-compose.yml`).
- App env: set `REDIS_URL=redis://localhost:6379/0` (defaults to this when using compose).

## Migrations
Run inside backend container: `alembic upgrade head`.

## Development
- Hot reload: uses `docker-compose.override.yml` to mount code and `--reload`.
- Requirements: see `backend/requirements.txt`.

## Soft Launch Onboarding Guide
- Enable soft launch: set `SOFT_LAUNCH_ENABLED=true` and list pilot slugs in `SOFT_LAUNCH_TENANT_SLUGS`, or use the admin API/CLI to toggle per tenant.
- Onboard a pilot: run `python -m app.management.onboard_pilot --name "Pilot Co" --slug pilot-co --email owner@example.com --password Secret123!`.
- Monitor usage/errors: use admin endpoints `/api/v1/admin/tenants/{tenant_id}/overview` or frontend pages `/admin/tenants` and tenant detail.
- Collect feedback: pilot users click “Send Feedback” in-app; admins view at `/admin/feedback`.
- Observability: check Prometheus/Grafana (default 9090/3001) and error feed `/api/v1/admin/errors/recent`.
