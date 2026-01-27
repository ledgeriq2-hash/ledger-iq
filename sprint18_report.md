# Sprint 18 Report — Vendors + Purchase Bills (AP Core)

## Scope summary
- Extended vendors with contact/address fields and added a status update endpoint.
- Hardened purchase invoices to function as AP purchase bills with draft/post/reverse flow, server-side totals, idempotency guards, and journal entry linkage.
- Added purchase bill endpoints (including line CRUD) and vendor-scoped bill routes.
- Added verifier covering AP posting, reversal, period locks, and tenant isolation.

## Migrations
```
cd backend
python -m alembic upgrade head
```

## Verifier
```
python verify_sprint18_vendors_purchase_bills.py
```

## Assumptions / Notes
- AP control account is resolved via existing `AccountMapping` key `AP_CONTROL`.
- Bill numbers are generated as `BILL-000001` when omitted.
- Purchase bills are implemented on the existing `purchase_invoices` table with a new `/api/v1/purchase-bills` route alias.
- Vendor contacts table was not added (optional scope).
