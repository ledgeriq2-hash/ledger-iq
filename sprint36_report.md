# Sprint 36 Report — Tenant bootstrap + zero-friction local dev

Summary
- Added a dev-only bootstrap endpoint to create the first tenant + admin without requiring X-Tenant-Id.
- Tenant middleware exempts the bootstrap route while preserving tenant enforcement elsewhere.
- TenantSelect auto-selects when exactly one tenant exists, and provides a dev bootstrap CTA when none exist.

Endpoints + flags
- `POST /api/v1/dev/bootstrap` (dev-only)
  - Allowed when `ENVIRONMENT=development` OR `APP_ENV=dev` OR `LEDGERIQ_ALLOW_DEV_ENDPOINTS=1`
  - Returns: `tenant_id`, `admin_email`, `access_token`, `tenant`

Bootstrap locally (examples)
```powershell
curl -X POST http://localhost:8000/api/v1/dev/bootstrap ^
  -H "Content-Type: application/json" ^
  -d "{\"tenant\":{\"name\":\"Demo Company\",\"slug\":\"demo\"},\"admin\":{\"email\":\"admin@demo.local\",\"password\":\"Test1234\",\"full_name\":\"Demo Admin\"}}"
```

Manual UI smoke
- Open http://localhost:5173
- Run: `localStorage.removeItem("tenant_id")`
- If present from older builds: `localStorage.removeItem("tenant_slug")`
- Reload: if exactly one tenant exists, the app should auto-select and continue.
- If zero tenants exist, click “Create demo company”; it should set `tenant_id` and continue.

Validation commands
```powershell
docker compose up -d --build
docker compose exec -T backend sh -lc "alembic upgrade head"
python backend/scripts/verify_sprint36_tenant_bootstrap.py
python backend/scripts/verify_release_gate.py
docker compose exec -T frontend sh -lc "npm run lint && npm run build"
```

Files changed
- backend/app/api/v1/dev.py
- backend/app/middleware/tenant.py
- frontend/src/contexts/AuthContext.jsx
- frontend/src/pages/onboarding/TenantSelect.jsx
- backend/scripts/verify_sprint36_tenant_bootstrap.py
- sprint36_report.md
