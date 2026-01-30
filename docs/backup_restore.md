# Backup & Restore (Docker Postgres)

These scripts use the running Docker Postgres container to create and restore plain SQL backups.

## Backup

```powershell
# From repo root
.\scripts\backup_db.ps1
```

Optional parameters:

```powershell
.\scripts\backup_db.ps1 -Container ledgeriq-postgres-1 -Database ledgeriq -User ledgeriq
```

Environment overrides:

```
POSTGRES_CONTAINER=ledgeriq-postgres-1
POSTGRES_DB=ledgeriq
POSTGRES_USER=ledgeriq
```

Backups are stored in `./backups/` with a timestamped filename.

## Restore

```powershell
.\scripts\restore_db.ps1 -InputFile .\backups\ledgeriq_20260130_120000.sql
```

Optional parameters:

```powershell
.\scripts\restore_db.ps1 -InputFile .\backups\ledgeriq_20260130_120000.sql -Container ledgeriq-postgres-1 -Database ledgeriq -User ledgeriq
```

## Notes
- The scripts will try `docker compose ps -q postgres` if `POSTGRES_CONTAINER` is not set.
- `restore_db.ps1` uses `psql -v ON_ERROR_STOP=1` to stop on errors.
