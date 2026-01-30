# Sprint 26 Report — Production Readiness Core

Summary
- Unified error envelope across exception handlers with request_id propagation.
- Added /healthz and /readyz endpoints (DB + Redis readiness).
- Implemented Redis-backed fixed-window rate limiter for selected public portal routes.
- Added PowerShell backup/restore scripts for Docker Postgres and documentation.
- Added verifier for request IDs, error envelope, readiness, and rate limiting.

How to run verifier
```powershell
python backend/scripts/verify_sprint26_production_readiness.py
```

Manual checks
- GET http://localhost:8000/healthz returns 200 and includes `X-Request-ID` header.
- GET http://localhost:8000/readyz returns 200 when Postgres + Redis are reachable.
- Public portal summary endpoint returns 429 after repeated requests with `Retry-After` header and unified error envelope.

Files touched
- backend/app/shared/errors.py
- backend/app/core/exceptions.py
- backend/app/core/rate_limit.py
- backend/app/main.py
- backend/scripts/verify_sprint26_production_readiness.py
- scripts/backup_db.ps1
- scripts/restore_db.ps1
- docs/backup_restore.md
- sprint26_report.md
