# Sprint 35 Report — Tenant selector focus (explicit selection)

Summary
- Removed single-tenant auto-select; tenant selection is always explicit when `tenant_id` is missing/invalid.
- Preserved legacy `tenant_slug` → `tenant_id` migration.
- Updated verifiers to reflect explicit selection flow.

Selection flow
- Read `tenant_id` from localStorage.
- If legacy `tenant_slug` exists, map it to a tenant id via `/api/v1/dev/tenants`, set `tenant_id`, then remove `tenant_slug`.
- Fetch `/api/v1/dev/tenants`.
- If stored `tenant_id` is valid, keep it.
- Otherwise clear it and require explicit selection in TenantSelect.

Validation commands
```powershell
docker compose up -d --build
docker compose exec -T backend sh -lc "alembic upgrade head"
python backend/scripts/verify_sprint34_tenantless_ux.py
python backend/scripts/verify_sprint35_tenant_selector_flow.py
python backend/scripts/verify_release_gate.py
docker compose exec -T frontend sh -lc "npm run lint && npm run build"
```

Manual UI checklist
- Open http://localhost:5173
- Run: `localStorage.removeItem("tenant_id")`
- If present from older builds: `localStorage.removeItem("tenant_slug")`
- Reload: TenantSelect should appear, even if only one tenant exists.
- Selecting a tenant should set `tenant_id` and navigate.
- If no tenants exist, TenantSelect should show a friendly empty state with guidance.

Files changed
- frontend/src/contexts/AuthContext.jsx
- frontend/src/pages/onboarding/TenantSelect.jsx
- backend/scripts/verify_sprint34_tenantless_ux.py
- backend/scripts/verify_sprint35_tenant_selector_flow.py
- sprint35_report.md
