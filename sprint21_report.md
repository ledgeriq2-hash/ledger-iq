# Sprint 21 Report — Inventory Core (Stock Ledger)

Summary:
- Implemented immutable stock ledger moves with signed quantities, reversal linking, and base-unit aggregation.
- Added inventory units (ratio_to_base) and product code generation with active status handling.
- Integrated stock posting/reversal with sales invoices and purchase bills; added read-only stock balance/ledger endpoints.

Design notes:
- Inventory units are stored in `inventory_units` with `ratio_to_base` (base unit = 1).
- Stock moves are immutable ledger entries; balances are computed via sum of signed `base_quantity`.
- Period locks are enforced in posting/reversal flows and stock ledger service.

Posting & reversal guarantees:
- Posting creates stock moves once per source (SALE/PURCHASE) and rejects duplicates.
- OUT moves validate available balance using SELECT … FOR UPDATE on ledger aggregation.
- Reversal creates new linked moves (`reversed_stock_move_id`) with opposite direction; idempotent if reversals already exist.

Verifier output:
- `SPRINT 21 VERIFIED OK`

How to run:
- Migrations:
  - cd backend
  - python -m alembic upgrade head
- Verifier:
  - python verify_sprint21_inventory_stock_ledger.py
