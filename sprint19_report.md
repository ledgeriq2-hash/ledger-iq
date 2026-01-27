# Sprint 19 Report — AR/AP Settlements (Receipts + Payments)

## Scope summary
- Added customer receipts and vendor payments with allocation tables and draft/post/reverse lifecycle.
- Implemented posting logic with unapplied handling (customer credits + vendor prepayments) and idempotency guards.
- Added receipt/payment routers, customer/vendor scoped endpoints, and allocation CRUD.
- Added verifier covering allocations, posting, reversals, period locks, and tenant isolation.

## Migrations
```
cd backend
python -m alembic upgrade head
```

## Verifier
```
python verify_sprint19_settlements_ar_ap.py
```

## Assumptions / Notes
- AR/AP control accounts are resolved via `AccountMapping` keys `AR_CONTROL` and `AP_CONTROL`.
- Unapplied receipts use `AccountMapping` key `CUSTOMER_CREDIT`; unapplied payments use `VENDOR_PREPAY`.
- Receipt numbers are generated as `RCPT-000001` and payment numbers as `PAY-000001` when omitted.
- Purchase bills are the existing `purchase_invoices` table surfaced via `/api/v1/purchase-bills`.
