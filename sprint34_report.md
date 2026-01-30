# Sprint 34 Report — Tenantless UX (Single-tenant auto-select)

Summary
- AuthContext validates `tenant_id` against the tenants list and auto-selects when exactly one tenant exists.
- TenantSelect auto-redirects for single-tenant setups, shows the selector only for multiple tenants, and provides a friendly empty state when none exist.

How auto-select works
- Read `tenant_id` from localStorage.
- If legacy `tenant_slug` exists, map it to a tenant id via `/api/v1/dev/tenants`, set `tenant_id`, then remove `tenant_slug`.
- Fetch `/api/v1/dev/tenants`.
- If stored `tenant_id` is valid, keep it.
- Else if exactly one tenant exists, set `tenant_id` and proceed.
- Else show the TenantSelect UI.

Validation commands
```powershell
docker compose up -d --build
docker compose exec -T backend sh -lc "alembic upgrade head"
python backend/scripts/verify_sprint34_tenantless_ux.py
python backend/scripts/verify_release_gate.py
docker compose exec -T frontend sh -lc "npm run lint && npm run build"
```

Manual UI checklist
- Open http://localhost:5173
- Run: `localStorage.removeItem("tenant_id")`
- If present from older builds: `localStorage.removeItem("tenant_slug")`
- Reload: if exactly one tenant exists, the app should skip TenantSelect and land in the app.
- If multiple tenants exist, TenantSelect should display the list and allow selection.
- If no tenants exist, TenantSelect should show “No tenants found” with a Reload button.

Files changed
- frontend/src/contexts/AuthContext.jsx
- frontend/src/pages/onboarding/TenantSelect.jsx
- backend/scripts/verify_sprint34_tenantless_ux.py
- sprint34_report.md
