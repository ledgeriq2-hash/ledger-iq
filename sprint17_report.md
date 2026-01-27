# Sprint 17 Report — Customers + Sales Invoices (AR Core)

## Scope summary
- Added customer address fields and status endpoint.
- Enabled draft sales invoices with optional invoice number, server-side totals, posting journal entry linkage, and reversal linkage.
- Added sales invoice line CRUD endpoints (draft-only) with server-side amount calculation and tenant isolation safeguards.
- Implemented invoice number generation (INV-000001…) and idempotency guards for posting/reversing.
- Added verifier for end-to-end AR flow with period lock and tenant isolation checks.

## Migrations
```
cd backend
python -m alembic upgrade head
```

## Verifier
```
python verify_sprint17_customers_sales_invoices.py
```

## Assumptions / Notes
- AR control account is resolved via existing `AccountMapping` key `AR_CONTROL`.
- Line totals are computed as `quantity * unit_price`; any client-provided amount must match.
- Customer contacts table was not added (optional scope).
