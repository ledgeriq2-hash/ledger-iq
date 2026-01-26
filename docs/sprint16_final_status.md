# Sprint 16 Final Status

## What was fixed
- Added a production-grade PowerShell remediation script to grant missing Postgres privileges to the `ledgeriq` role.
- Added a verifier that confirms Alembic migrations can run and basic SELECTs succeed.
- Added a service-level AI ingestion verifier (no HTTP required).

## Sprint 16 scope note
Sprint 16 validates AI ingest at the **service layer**. HTTP exposure of AI endpoints is intentionally deferred to a later sprint.

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

2) Ensure a tenant exists (if needed)
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

5) Verify AI ingestion and insights retrieval (service-level, no server required)
Requirements:
- `AI_TEST_TENANT_ID` set in your environment.

Command:
```
python verify_sprint16_ai_ingest.py
```
Expected output:
```
OK
```

## Troubleshooting
- 404 from `/api/v1/dev/tenants`: dev endpoints disabled; use the Postgres query option.
- Tenant mismatch: ensure `AI_TEST_TENANT_ID` is set to the correct tenant UUID.

## Final verdict criteria
Sprint 16 is unblocked when all three steps complete successfully and the verifiers print `OK`.
