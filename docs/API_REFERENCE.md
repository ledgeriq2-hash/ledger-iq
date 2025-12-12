# API Reference (v1)

Base URL: `/api/v1`. Auth uses `Authorization: Bearer <JWT>` unless noted (portal tokens use path token).

## Auth
- `POST /auth/register` – create tenant + admin. Body: tenant `{name, slug}`, admin `{email, password, full_name}`. Returns tokens + tenant.
- `POST /auth/login` – body `{tenant_slug, email, password}`. Returns access/refresh tokens.
- `POST /auth/refresh` – body `{refresh_token}` → new tokens.

## Tenants & Users
- `GET /tenants/me` – current tenant info (auth).
- `PATCH /tenants/me` – update settings (chart_of_accounts_mapping, portal). Auth.
- `GET /users/me` – current user. Auth.
- `POST /users/` – create user; role-based. Auth.
- `GET /users/` – list users.

## Customers
- `GET /customers/` – list (tenant scoped).
- `POST /customers/` – create. Body `{name, email, ...}`.
- `GET /customers/{id}` – fetch.
- `PATCH /customers/{id}` – update.
- `DELETE /customers/{id}` – soft-delete.

## Suppliers
- `GET /suppliers/`
- `POST /suppliers/`
- `GET /suppliers/{id}`
- `PATCH /suppliers/{id}`
- `DELETE /suppliers/{id}`

## Invoices
- `GET /invoices/` – query params: `page`, `page_size`.
- `POST /invoices/` – body `{customer_id, issue_date, due_date, status, currency, items[]}`.
- `GET /invoices/{id}`
- `PATCH /invoices/{id}`
- `DELETE /invoices/{id}`

### Recurring Invoices
- `GET /recurring-invoices/` – list with `page`, `page_size`, optional `frequency` filter.
- `POST /recurring-invoices/` – body `{customer_id, frequency (daily|weekly|monthly|custom), interval, day_of_month?, next_run_at?, template}` where `template` follows invoice create shape.
- `GET /recurring-invoices/{id}`
- `PATCH /recurring-invoices/{id}`
- `DELETE /recurring-invoices/{id}`
- `POST /recurring-invoices/{id}/run` – manually generate child invoice now.

### Inventory
- `GET /inventory/movements` – filters: `product_id`, `movement_type (IN|OUT|ADJUST)`, `reference_type (INVOICE|PURCHASE|MANUAL)`, `page`, `page_size`.
- `POST /inventory/movements` – body `{product_id, quantity>0, movement_type, reference_type?, reference_id?}`.
- `GET /inventory/movements/{id}`, `PATCH /inventory/movements/{id}`, `DELETE /inventory/movements/{id}`.
- `GET /inventory/summary` – per-product stock and valuation `{items:[{product_id, stock_quantity, valuation}], total_value}`.

## Payments
- `GET /payments/`
- `POST /payments/` – body `{customer_id, invoice_id?, amount, method, paid_at?}`.
- `GET /payments/{id}`
- `PATCH /payments/{id}`
- `DELETE /payments/{id}`

## Expenses
- `GET /expenses/`
- `POST /expenses/` – body `{supplier_id?, category, amount, currency, expense_date, description}`.
- `GET /expenses/{id}`
- `PATCH /expenses/{id}`
- `DELETE /expenses/{id}`

## Reports
- `GET /reports/income-statement`
- `GET /reports/balance-sheet`
- `GET /reports/cashflow`
- `GET /reports/trial-balance`
- Query params: `from`, `to`, `as_of` depending on report. Auth.

## Portal (tokenized, no JWT)
- Customer:
  - `POST /portal/customer/token` (auth) → portal link.
  - `GET /portal/customer/{token}` – overview (customer, invoices, payments, settings, activity).
  - `GET /portal/customer/{token}/invoices`
  - `GET /portal/customer/{token}/payments`
  - `GET /portal/customer/{token}/settings`
  - `PATCH /portal/customer/{token}/settings`
- Supplier:
  - `POST /portal/supplier/token` (auth) → portal link.
  - `GET /portal/supplier/{token}` – overview (supplier, orders=expenses, payments, settings).
  - `GET /portal/supplier/{token}/orders`
  - `GET /portal/supplier/{token}/payments`
  - `GET /portal/supplier/{token}/settings`
  - `PATCH /portal/supplier/{token}/settings`

Errors: JSON `{success:false,error:{code,message},request_id}` with `X-Request-ID`.

## AI
- `POST /ai/forecast` – body `{data|revenues, horizon_days, window?, alpha?}` → `{forecast, intervals, baseline, mape, rmse}`.
- `POST /ai/anomaly` – body `{data|revenues, threshold?, method?, window?}` → anomalies with z-scores/IQR.
- `POST /ai/summary` – body `{balance_sheet?, income_statement?}` → `{summary}`.
- `GET /ai/overview` – tenant scoped overview `{anomalies_count, forecast_summary:{text}, alerts[]}`.
- Logs:
  - `GET /ai/logs`
  - `GET /ai/logs/{id}`
  - `DELETE /ai/logs/{id}`

## Notifications/Feedback
- `POST /feedback/` – tenant feedback (rate limited).
- `GET /notifications/` – list current user notifications.

## Admin/Billing (selected)
- `POST /billing/stripe/webhook` – Stripe hook (unauth, signed).
- `POST /admin/seed` – seeded data (role restricted).

### Response shape notes
- Collections: usually `{items: [...]}` or paged `{items,total}`.
- Portal: see portal endpoints; invoices/payments match public schema fields (`id`, amounts, status, currency, dates).
- Dates ISO8601, UUIDs as strings, decimals as strings.

### Example: create invoice
```http
POST /api/v1/invoices/
Authorization: Bearer <token>
Content-Type: application/json

{
  "customer_id": "uuid",
  "issue_date": "2025-01-01",
  "due_date": "2025-01-15",
  "status": "SENT",
  "currency": "USD",
  "items": [
    {"description": "Service", "quantity": "1", "unit_price": "100.00", "tax_rate": "0"}
  ]
}
```
Response `201` with invoice payload incl. `total_amount`.
