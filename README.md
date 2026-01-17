# Ledger IQ (Local dev with Docker)

Runs locally with:
- Backend: FastAPI + Postgres (via docker-compose)
- Frontend: Vite + React

Auth/JWT/MFA/RBAC/rate-limits are disabled for local runtime. All API calls require `X-Tenant-Id` and accept optional `X-Actor-Id`.

## Environment setup
- Backend: copy `backend/.env.example` to `.env.development` (repo root or `backend/`) and fill in any required values for your environment (or copy to `backend/.env` and set `ENV_FILE=backend/.env`). For docker-compose Postgres, set `DATABASE_URL=postgresql+asyncpg://ledgeriq:ledgeriq_password@localhost:5432/ledgeriq`.
- Local optional routes: set `FEATURE_OPTIONAL_ROUTES=true` to expose dashboard, reports, payments, AI/ML, admin, settings routes.
- Frontend: copy `frontend/.env.example` to `frontend/.env` (or keep using PowerShell env vars as shown below).
  - If the frontend is proxied via nginx at `http://localhost`, `VITE_API_ORIGIN` can be left unset (defaults to current origin). To override, set `VITE_API_ORIGIN=http://localhost`.

Note: for local API usage via curl/Postman, keep `CSRF_ENABLED=false` in your dev env file.
If you keep CSRF enabled in local dev, POSTs to `/api/v1/ai/*` are CSRF-exempt (dev-only) so you can call the AI forecast/anomaly endpoints without CSRF tokens.

## Start dependencies (Postgres + Redis)
```powershell
docker compose up -d
```

## Seed demo tenant (Docker Compose)
Create a demo tenant, owner user, and sample data.

```powershell
$env:DEMO_OWNER_PASSWORD = "Secret123!"
docker compose exec -e DEMO_OWNER_PASSWORD=$env:DEMO_OWNER_PASSWORD backend python -m app.management.demo_data
```

Then login at `http://localhost/login` using:
- Tenant slug: `demo-ledger`
- Email: `demo.owner@example.com`
- Password: the value you set in `DEMO_OWNER_PASSWORD`

## Backend (Windows PowerShell)
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# optional: create a local env file (git-ignored)
Copy-Item ..\.env.example ..\.env.development -Force
Copy-Item .\.env.example .\.env.development -Force

# run migrations
$env:ENVIRONMENT = "development"
alembic upgrade head

# run API
uvicorn app.main:app --reload --port 8000
```

Health: `http://localhost:8000/health`

## Create a tenant id for local requests
```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m app.management.onboard_pilot --name "Local Tenant" --slug local-tenant --email owner@example.com --password Secret123!
```
Copy the printed `tenant.id` value (UUID) for the next step.

## Get tenant ids in dev (no headers needed)
Only available when `ENVIRONMENT` is not production and `DEBUG=true`.

```powershell
Invoke-RestMethod -Method Get "http://localhost:8000/api/v1/dev/tenants"
```

## Frontend (Windows PowerShell)
```powershell
cd frontend
npm ci

# optional: use a Vite env file (git-ignored)
Copy-Item .\.env.example .\.env -Force

# required for all API calls
$env:VITE_TENANT_ID = "<paste-tenant-uuid>"
# optional (for audit/logging)
$env:VITE_ACTOR_ID = "<optional-actor-uuid>"

npm run dev
```

Frontend: `http://localhost:5173`

## Sprint 2 verification (COA + Ledger)
```powershell
$tenantId = "<paste-tenant-uuid>"

# migrate + seed
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.initial_data

# fetch system accounts
$accounts = Invoke-RestMethod -Method Get "http://localhost:8000/api/v1/accounts" `
  -Headers @{ "X-Tenant-Id" = $tenantId }
$cashId = ($accounts.items | Where-Object { $_.code -eq "1100" }).id
$revenueId = ($accounts.items | Where-Object { $_.code -eq "4000" }).id

# create manual journal draft
$draft = Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/journals/manual" `
  -Headers @{ "X-Tenant-Id" = $tenantId } `
  -ContentType "application/json" `
  -Body (@{
    entry_date = (Get-Date).ToString("yyyy-MM-dd")
    base_currency = "USD"
    memo = "Sprint 2 test entry"
    source_type = "manual"
    lines = @(
      @{ account_id = $cashId; debit_amount = 100; credit_amount = 0; line_currency = "USD" }
      @{ account_id = $revenueId; debit_amount = 0; credit_amount = 100; line_currency = "USD" }
    )
  } | ConvertTo-Json -Depth 6)

# post draft
Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/journals/$($draft.id)/post" `
  -Headers @{ "X-Tenant-Id" = $tenantId }

# reverse posted entry
Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/journals/$($draft.id)/reverse" `
  -Headers @{ "X-Tenant-Id" = $tenantId } `
  -ContentType "application/json" `
  -Body (@{ reason = "Sprint 2 reversal" } | ConvertTo-Json)
```

## Call AI endpoints (PowerShell)
All API calls require `X-Tenant-Id` (UUID). These examples work in local dev even if `CSRF_ENABLED=true`.

```powershell
$tenantId = "<paste-tenant-uuid>"

Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/ai/forecast" `
  -Headers @{ "X-Tenant-Id" = $tenantId } `
  -ContentType "application/json" `
  -Body (@{ horizon_days = 30; data = @() } | ConvertTo-Json -Depth 10)

Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/ai/anomaly" `
  -Headers @{ "X-Tenant-Id" = $tenantId } `
  -ContentType "application/json" `
  -Body (@{ data = @() } | ConvertTo-Json -Depth 10)
```

## Call AI endpoints (curl)
```bash
tenantId="<paste-tenant-uuid>"

curl -sS -X POST "http://localhost:8000/api/v1/ai/forecast" \
  -H "X-Tenant-Id: $tenantId" \
  -H "Content-Type: application/json" \
  -d '{"horizon_days":30,"data":[]}'
```

## Export revenue series (PowerShell)
```powershell
$tenantId = "<paste-tenant-uuid>"

Invoke-RestMethod -Method Get "http://localhost:8000/api/v1/ml/exports/revenue_series?granularity=month&limit=1000" `
  -Headers @{ "X-Tenant-Id" = $tenantId }
```

## Export revenue series (curl)
```bash
tenantId="<paste-tenant-uuid>"
curl -sS "http://localhost:8000/api/v1/ml/exports/revenue_series?granularity=month&limit=1000" \
  -H "X-Tenant-Id: $tenantId"
```

## Ingest ML prediction (PowerShell)
In local dev, `POST /api/v1/ml/predictions/ingest` and `POST /api/v1/ml/snapshots` are CSRF-exempt so an external ML runner can ingest without managing CSRF tokens.

```powershell
$tenantId = "<paste-tenant-uuid>"

$snapshotId = (Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/ml/snapshots" `
  -Headers @{ "X-Tenant-Id" = $tenantId } `
  -ContentType "application/json" `
  -Body (@{
    from_date = "2025-01-01"
    to_date = "2025-01-31"
    granularity = "day"
    filters = @{}
    rows_count = 0
    content_hash = "sha256:local"
  } | ConvertTo-Json -Depth 10)).snapshot_id

Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/ml/predictions/ingest" `
  -Headers @{ "X-Tenant-Id" = $tenantId } `
  -ContentType "application/json" `
  -Body (@{
    prediction_type = "forecast"
    horizon = 30
    granularity = "day"
    from_date = "2025-01-01"
    to_date = "2025-01-31"
    series = @{ labels = @("2025-01-01"); values = @(123.45) }
    model_version = "1.0.0"
    data_snapshot_id = $snapshotId
    metrics = @{}
    params = @{}
    trigger = "local"
  } | ConvertTo-Json -Depth 10)
```

## Ingest ML prediction (curl)
```bash
tenantId="<paste-tenant-uuid>"
snapshotId="<paste-snapshot-uuid>"

curl -sS -X POST "http://localhost:8000/api/v1/ml/predictions/ingest" \
  -H "X-Tenant-Id: $tenantId" \
  -H "Content-Type: application/json" \
  -d "{\"prediction_type\":\"forecast\",\"horizon\":30,\"granularity\":\"day\",\"from_date\":\"2025-01-01\",\"to_date\":\"2025-01-31\",\"series\":{\"labels\":[\"2025-01-01\"],\"values\":[123.45]},\"model_version\":\"1.0.0\",\"data_snapshot_id\":\"$snapshotId\",\"metrics\":{},\"params\":{},\"trigger\":\"local\"}"
```

## Get latest prediction (PowerShell)
```powershell
$tenantId = "<paste-tenant-uuid>"
Invoke-RestMethod -Method Get "http://localhost:8000/api/v1/ml/predictions/latest?prediction_type=forecast" `
  -Headers @{ "X-Tenant-Id" = $tenantId }
```

## Get latest prediction (curl)
```bash
tenantId="<paste-tenant-uuid>"
curl -sS "http://localhost:8000/api/v1/ml/predictions/latest?prediction_type=forecast" \
  -H "X-Tenant-Id: $tenantId"
```
