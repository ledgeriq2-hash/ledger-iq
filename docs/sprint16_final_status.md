# Sprint 16 Final Status

## What was fixed
- Added a production-grade PowerShell remediation script to grant missing Postgres privileges to the `ledgeriq` role.
- Added a verifier that confirms Alembic migrations can run and basic SELECTs succeed.
- Added an end-to-end AI ingestion verifier that posts a run and fetches insights.

## How to run

1) Fix DB privileges (PowerShell)
```
PowerShell -ExecutionPolicy Bypass -File tools\fix_db_privileges.ps1
```
Expected output:
```
Privileges updated successfully.
```
Notes:
- To list containers: `docker ps`
- The script auto-detects the admin role from `POSTGRES_USER` inside the container, then falls back to common candidates (`postgres`, `root`, `admin`, `ledgeriq`, `ledgeriqlocal`).
- The script prefers the DB name from `DATABASE_URL` and warns if it differs from container `POSTGRES_DB`.

2) Get a JWT for API calls

Windows (PowerShell, dot-sourced so the token is set in your shell):
```
. .\scripts\get_test_jwt.ps1 -BaseUrl http://127.0.0.1:8000 -Email owner@example.com -Password "Secret123!" -Tenant local-tenant
```

macOS/Linux (bash, sourced):
```
source scripts/get_test_jwt.sh --base-url http://127.0.0.1:8000 --email owner@example.com --password "Secret123!" --tenant local-tenant
```

The script reads:
- `AI_BASE_URL` or `BASE_URL` (fallback `AI_TEST_BASE_URL`, default `http://127.0.0.1:8000`)
- `LOGIN_EMAIL`/`LOGIN_PASSWORD` or `LEDGERIQ_ADMIN_EMAIL`/`LEDGERIQ_ADMIN_PASSWORD`
- `LOGIN_TENANT` or `TENANT_ID` or `TENANT_SLUG`
It also sets `AI_TEST_TENANT_ID` automatically if the login response includes `tenant.id`.

If you have no tenant/user yet, create one (from README):
```
cd backend
python -m app.management.onboard_pilot --name "Local Tenant" --slug local-tenant --email owner@example.com --password Secret123!
```
Copy the printed `tenant.id` for `AI_TEST_TENANT_ID`.

3) Find the tenant id (deterministic options)

Option A: Dev endpoint (works in development environments)
```
curl http://127.0.0.1:8000/api/v1/dev/tenants
```
Set the tenant id in your shell:

PowerShell:
```
$env:AI_TEST_TENANT_ID = "<tenant-uuid>"
```

bash:
```
export AI_TEST_TENANT_ID="<tenant-uuid>"
```

Option B: Postgres query (Docker)
```
docker ps
docker exec -it <container_id> psql -U <admin_user> -d <db_name> -c "SELECT id, slug FROM tenants ORDER BY created_at DESC LIMIT 5;"
```

4) Verify DB privileges
```
python verify_sprint16_db_privileges.py
```
Expected output:
```
OK
```

5) Verify AI ingestion and insights retrieval
Requirements:
- `AI_TEST_JWT` and `AI_TEST_TENANT_ID` set in your environment.
- API running at `AI_BASE_URL` or `BASE_URL` (default `http://127.0.0.1:8000`).

Command:
```
python verify_sprint16_ai_ingest.py
```
Expected output:
```
OK
```

## Troubleshooting
- 401/403: verify login credentials and tenant slug/id, then re-run `get_test_jwt`.
- 404 from `/api/v1/dev/tenants`: dev endpoints disabled; use the Postgres query option.
- Connection refused: confirm backend is running and `AI_BASE_URL`/`BASE_URL` is correct.
- Tenant mismatch: ensure `AI_TEST_TENANT_ID` matches the tenant used during login.

## CSRF-mode environments
If `/api/v1/auth/login` returns `csrf_failed`, use the local CLI:

```
cd backend
python -m app.management.issue_test_jwt --tenant-id <tenant-uuid> --email <user-email>
```

Re-run the helper scripts or set `AI_TEST_JWT`/`AI_TEST_TENANT_ID` from the printed export lines.

## Final verdict criteria
Sprint 16 is unblocked when all three steps complete successfully and the verifiers print `OK`.
