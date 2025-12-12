# Disaster Recovery

## Backups
- Database: use scheduled pg_dump or base backups (see `scripts/backup_db.sh` if configured). Store in offsite bucket (S3-compatible). Retain encryption keys separately.
- Redis: snapshot not critical; recreate. Persist only if AOF enabled.
- Images/config: Docker images in registry (GHCR); configs in git; secrets in vault/secret store.

## Restore steps
1. Provision clean Postgres of same major version.
2. Download latest verified backup from bucket.
3. Restore: `pg_restore`/`psql < dump.sql` to target DB.
4. Apply migrations: `alembic upgrade head`.
5. Redeploy services: `docker compose pull && docker compose up -d`.
6. Point app to restored DB/Redis via env.

## Verification
- Run health check `/health`.
- Run smoke tests: login, create customer/invoice/payment, portal token, AI overview.
- Check metrics `/metrics` and Grafana dashboards load.
- Review logs for errors on startup.

## RTO/RPO goals
- Target RTO: ≤ 60 minutes.
- Target RPO: ≤ 15 minutes (align backup schedule accordingly).

## Notes
- Keep SSH keys and registry creds backed up in secret manager.
- Document last-good backup timestamp; test restores quarterly.
