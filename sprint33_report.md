# Sprint 33 Report — Stability + Observability Quality Gate

Summary
- Ensured unhandled 500s return JSON error envelopes (no stack traces) by enforcing JSON on 500 responses.
- Added a dev-only endpoint to trigger controlled 500 responses for verification (guarded by dev env flags).
- Added a stability gate verifier to validate /healthz, /readyz, and 500 error envelopes.

Enable dev trigger locally
- In `docker-compose.override.yml`, add for backend env: `LEDGERIQ_ALLOW_DEV_ENDPOINTS=1` (or set `APP_ENV=dev` / `ENVIRONMENT=development`).

How to run verifiers
```powershell
docker compose down -v
docker compose build --no-cache backend
docker compose up -d --build
docker compose exec -T backend sh -lc "alembic upgrade head"
python backend/scripts/verify_sprint33_stability_gate.py
python backend/scripts/verify_release_gate.py
docker compose exec -T frontend sh -lc "npm run lint && npm run build"
```

Acceptance checklist
- /healthz returns 200 quickly with `X-Request-ID`.
- /readyz returns 200 after DB + Redis checks with `X-Request-ID`.
- Controlled 500 endpoint returns JSON error envelope with `X-Request-ID`.

Files changed
- backend/app/middleware/request_id.py
- backend/app/api/v1/dev.py
- backend/app/middleware/tenant.py
- backend/scripts/verify_sprint33_stability_gate.py
- sprint33_report.md
