# Sprint 32 Report — Request-ID Header Consistency

Summary
- Switched request ID middleware to ASGI-style header injection to ensure `X-Request-ID` is always present.
- Added verifier to confirm request-id headers on `/healthz` and `/api/v1/auth/register`.
- Auto-selects tenant when exactly one is available, preserving `tenant_id` storage.

How to run verifier
```powershell
python backend/scripts/verify_sprint32_request_id_headers.py
```

Local validation (Docker)
```powershell
docker compose up -d --build
python backend/scripts/verify_sprint32_request_id_headers.py
python backend/scripts/verify_sprint26_production_readiness.py
python backend/scripts/verify_release_gate.py
docker compose exec -T frontend sh -lc "npm run lint && npm run build"
```

UI tenant auto-select test
- Clear selection: `localStorage.removeItem("tenant_id")`
- Reload `http://localhost:5173`
- If only one tenant exists, it should auto-select and allow navigation.

UI tenant auto-select (local)
- Uses `/api/v1/dev/tenants` to auto-select when exactly one tenant exists.

Files changed
- backend/app/middleware/request_id.py
- frontend/src/contexts/AuthContext.jsx
- frontend/src/pages/onboarding/TenantSelect.jsx
- backend/scripts/verify_sprint32_request_id_headers.py
- sprint32_report.md
