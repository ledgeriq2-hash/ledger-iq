# Production Checklist

Required env vars (minimum)
- `ENVIRONMENT=production`
- `DATABASE_URL=postgresql+asyncpg://...`
- `REDIS_URL=redis://...`
- `JWT_SECRET_KEY` and `JWT_REFRESH_SECRET_KEY`
- `CORS_ORIGINS` (comma-separated) for any allowed frontend origins
- `FRONTEND_URL` (if used by email templates or redirects)

HTTPS / TLS
- Terminate TLS at the edge (load balancer / reverse proxy).
- Ensure the proxy forwards `X-Forwarded-Proto=https` so downstream services can enforce HTTPS.
- HSTS is enabled only when `ENVIRONMENT=production`.

CORS hardening
- `CORS_ORIGINS` accepts a comma-separated list or JSON array.
- Do not use `*` in production unless explicitly intended.
- Default local-dev origins: `http://localhost:5173`, `http://127.0.0.1:5173`.

Backups (Sprint 26)
- Use `scripts/backup_db.ps1` to create timestamped dumps via docker compose.
- Use `scripts/restore_db.ps1` to restore from a dump file.
- Store backups off-host and validate restores periodically.

CI stability gate (Sprint 27)
- CI boots the Docker Compose stack, waits for `/healthz` and `/readyz`,
  runs `verify_sprint26_production_readiness.py`, then runs frontend lint/build.

