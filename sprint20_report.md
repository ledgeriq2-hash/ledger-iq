# Sprint 20 Report — Taxes + Multi-Currency + FX Revaluation

Summary:
- Added VAT fields and FX/base-currency capture for sales invoices, purchase bills, receipts, and payments.
- Implemented FX revaluation runs with idempotent per-period/currency guards and base-currency postings.
- Extended services to enforce FX rate requirements, currency matching for allocations, and VAT posting lines.

Files changed:
- backend/alembic/versions/0020_sprint20_fx_tax.py
- backend/app/models/sales_invoice.py
- backend/app/models/purchase_invoice.py
- backend/app/models/sales_invoice_line.py
- backend/app/models/purchase_invoice_line.py
- backend/app/models/customer_receipt.py
- backend/app/models/vendor_payment.py
- backend/app/models/fx_revaluation_run.py
- backend/app/models/fx_revaluation_line.py
- backend/app/models/__init__.py
- backend/app/schemas/sales_invoice.py
- backend/app/schemas/purchase_invoice.py
- backend/app/schemas/customer_receipt.py
- backend/app/schemas/vendor_payment.py
- backend/app/schemas/fx_revaluation.py
- backend/app/schemas/__init__.py
- backend/app/services/sales_invoice_service.py
- backend/app/services/purchase_invoice_service.py
- backend/app/services/customer_receipt_service.py
- backend/app/services/vendor_payment_service.py
- backend/app/services/fx_revaluation_service.py
- backend/app/services/settings_service.py
- backend/app/services/__init__.py
- backend/app/api/v1/fx_revaluation.py
- backend/app/api/router.py
- verify_sprint20_taxes_fx_multicurrency.py
- sprint20_report.md

How to run:
- Migrations:
  - cd backend
  - python -m alembic upgrade head
- Verifier:
  - python verify_sprint20_taxes_fx_multicurrency.py

Assumptions / Notes:
- Base currency comes from tenant.settings_json["BASE_CURRENCY"], otherwise falls back to app settings currency (default USD).
- VAT mappings use AccountMapping keys OUTPUT_VAT / INPUT_VAT; FX revaluation uses FX_GAIN / FX_LOSS.
- AR/AP control mappings use AR_CONTROL / AP_CONTROL.
- FX/base amounts are rounded to 2 decimals; fx_rate stored with 6-decimal precision.
