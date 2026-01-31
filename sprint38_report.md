# Sprint 38 Report — Tenant finalization gate

Summary
- Added backend tenant inference: when the tenant header is missing, infer only if the authenticated user has exactly one accessible tenant; otherwise return a stable TENANT_REQUIRED envelope.
- Persisted tenant selection on the frontend with the new `ledgeriqlastTenantId` key, auto-selecting when valid and prompting for selection or demo bootstrap as needed.
- Added a verifier to exercise single-tenant inference and multi-tenant enforcement behavior.

Key behaviors
- Missing `X-Tenant-Id`:
  - Exactly one accessible tenant → request proceeds with inferred tenant.
  - Zero or multiple accessible tenants → 400 with `code=TENANT_REQUIRED`, `message="Tenant header is required"`, and hint.
- Frontend:
  - Stores last selected tenant in `ledgeriqlastTenantId`.
  - Auto-selects last tenant if still accessible.
  - Auto-selects when exactly one tenant is available.
  - Shows “Create demo company” CTA when no tenants exist (dev bootstrap with `seed_demo=true`).

Validation commands
```powershell
docker compose up -d --build
docker compose exec -T backend sh -lc "alembic upgrade head"
docker compose exec -T backend sh -lc "cd /app && python scripts/verify_sprint38_tenant_finalization.py"
docker compose exec -T backend sh -lc "cd /app && python scripts/verify_release_gate.py"
docker compose exec -T frontend sh -lc "npm run lint && npm run build"
```

Files changed
- backend/app/api/deps.py
- backend/app/middleware/tenant.py
- backend/app/services/user_service.py
- backend/scripts/verify_sprint38_tenant_finalization.py
- frontend/src/api/index.js
- frontend/src/components/layout/TenantSelector.jsx
- frontend/src/contexts/AuthContext.jsx
- frontend/src/layouts/MainLayout.jsx
- frontend/src/pages/onboarding/TenantSelect.jsx
- sprint38_report.md
