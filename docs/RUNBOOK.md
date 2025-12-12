# Runbook

## Health checks
- Backend: `GET /health` (200 => ok).
- Metrics: `GET /metrics` (Prometheus format).
- Frontend: open `/` and ensure app renders.

## Logs
- Backend (docker): `docker compose logs backend` (or `worker`, `beat`).
- Frontend (nginx): `docker compose logs frontend`.
- Prometheus/Grafana: `docker compose logs prometheus|grafana`.
- Local dev: uvicorn stdout; Playwright logs in `/tmp/frontend.log` and `/tmp/backend.log` in CI.

## Restart procedures
- Docker: `docker compose restart backend frontend worker beat`.
- Systemd (if used): `systemctl restart ledgeriq-backend`.
- Celery workers: `docker compose restart worker beat`.
- Redis/Postgres: `docker compose restart redis db`.

## Migrations
- Run `alembic upgrade head` inside backend image or venv.
- To create new migration: `alembic revision --autogenerate -m "..."` (review before apply).

## Incident playbooks
- 5xx spikes: check `/metrics`, backend logs, DB connectivity. Roll back recent deploy if needed.
- Auth failures (401/403 surge): verify JWT secrets env, clock skew, rate limiting blocks.
- DB errors: verify Postgres up, connection string, run migrations, check locks.
- Redis/rate-limit issues: ensure Redis reachable; clear hot keys if necessary.
- Portal token issues (404/403): validate token hash stored, check expiration and tenant mapping.
- AI endpoints slow/failing: inspect `ai_logs` table, recent deploy, metrics `ai_usage_total`, check external deps if any.

## Escalation checklist
- Capture request_id from error payload or `X-Request-ID`.
- Save logs + timestamps.
- Note deployment version/tag and env vars changes.
- Page on-call; if security-related, rotate tokens/keys as required.
