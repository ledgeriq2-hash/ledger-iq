# Sprint 37 Report — MVP closure gate (bootstrap + demo seed)

Summary
- Extended `/api/v1/dev/bootstrap` with `seed_demo=true` to seed a minimal demo dataset.
- Added a verifier to validate the MVP demo workflow and portal link creation.

Endpoints + flags
- `POST /api/v1/dev/bootstrap` (dev-only)
  - Allowed when `ENVIRONMENT=development` OR `APP_ENV=dev` OR `LEDGERIQ_ALLOW_DEV_ENDPOINTS=1`
  - Optional: `seed_demo=true` to create 1 customer, 1 vendor, 1 product, 1 draft sales invoice.

Bootstrap + seed locally (examples)
```powershell
$payload = @{
  seed_demo = $true
  tenant = @{ name = "Demo Company"; slug = "demo-company" }
  admin = @{ email = "admin@demo.local"; password = "Test1234"; full_name = "Demo Admin" }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/dev/bootstrap `
  -ContentType "application/json" -Body $payload
```

```bash
curl -X POST http://localhost:8000/api/v1/dev/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"seed_demo":true,"tenant":{"name":"Demo Company","slug":"demo-company"},"admin":{"email":"admin@demo.local","password":"Test1234","full_name":"Demo Admin"}}'
```

Manual UI smoke
- Open http://localhost:5173
- Run: `localStorage.removeItem("tenant_id")`
- If present from older builds: `localStorage.removeItem("tenant_slug")`
- Reload: if exactly one tenant exists, the app should auto-select and continue.
- If zero tenants exist, click “Create demo company” and verify demo data appears.

Validation commands
```powershell
docker compose up -d --build
docker compose exec -T backend sh -lc "alembic upgrade head"
docker compose exec -T backend sh -lc "cd /app && python scripts/verify_sprint37_mvp_gate.py"
docker compose exec -T backend sh -lc "cd /app && python scripts/verify_release_gate.py"
docker compose exec -T frontend sh -lc "npm run lint && npm run build"
```

Files changed
- backend/app/api/v1/dev.py
- backend/scripts/verify_sprint37_mvp_gate.py
- sprint37_report.md
