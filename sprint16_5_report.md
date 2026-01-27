# Sprint 16.5 Stability Gate Report

## Summary of stability improvements
- Enforced AI run immutability by rejecting duplicate ingests per tenant/model/scenario/payload and adding a unique DB index (with safe dedupe on migration).
- Hardened posting/reversal idempotency for sales/purchase invoices and treasury cash transactions (conflict on repeat attempts).
- Tightened tenant isolation by ensuring service-layer fetches include tenant filters instead of PK-only lookups.
- Added stability gate verifier covering tenant isolation, posting/reversal idempotency, period locks, and AI ingest safety.

## Files changed
- `backend/app/services/ai_runs_service.py`
- `backend/app/models/ai_run.py`
- `backend/alembic/versions/0016_5_stability_constraints.py`
- `backend/app/services/treasury_cash_service.py`
- `backend/app/services/sales_invoice_service.py`
- `backend/app/services/purchase_invoice_service.py`
- `backend/app/services/dimension_service.py`
- `backend/app/services/dimension_value_service.py`
- `backend/app/services/journal_line_dimension_service.py`
- `backend/app/services/journal_service.py`
- `backend/app/services/report_service.py`
- `backend/app/services/treasury_service.py`
- `verify_sprint16_5_stability_gate.py`
- `sprint16_5_report.md`

## How to run
Migrations:
```
cd backend
python -m alembic upgrade head
```

Verifier:
```
python verify_sprint16_5_stability_gate.py
```

## Constraints / indexes added
- Unique index on `ai_runs` to enforce immutability of AI run payloads per tenant/model/scenario:
  - `ux_ai_runs_client_model_version_dataset_scenario_payload_hash`
- Migration includes a one-time dedupe for existing AI runs with identical identity fields (keeps latest by `created_at`).

## Known limitations
- Period lock tests rely on the current date; ensure local system date is correct.
