# Sprint Fix Admin Access Report

## Summary
- Added `/api/v1/dev/ensure-owner` which, when `LEDGERIQ_ALLOW_DEV_ENDPOINTS=1` (or the existing dev guard), upserts the OWNER role for the authenticated dev user on the active tenant without weakening `require_roles`.
- Updated `backend/scripts/verify_fix_admin_access.py` to bootstrap a dev tenant, call `ensure-owner`, then hit the admin endpoint while asserting the new dev-only guard behaves correctly.

## Testing
1. Make sure `LEDGERIQ_ALLOW_DEV_ENDPOINTS=1` and the dev server is running.
2. `python backend/scripts/verify_fix_admin_access.py`
3. Observe `/api/v1/admin/tenants/` returns 200, and `/admin` UI opens without the permission warning.
