# Auth Flow (API Contract)

Overview
- Register a tenant + admin user to receive an access token.
- Use the access token with `Authorization: Bearer <token>` and include `X-Tenant-Id` for tenant-scoped APIs.
- Tokens are required for authenticated endpoints; public portal endpoints are tokenized separately.

Register (tenant + admin)
```
POST /api/v1/auth/register
```
Request body:
```json
{
  "tenant": { "name": "Acme", "slug": "acme" },
  "admin": { "email": "admin@acme.com", "password": "Test1234", "full_name": "Admin" }
}
```
Response includes `tenant` and `tokens.access_token`.

Use the access token
- Add `Authorization: Bearer <access_token>`
- Add `X-Tenant-Id: <tenant_id>`

Example (tenant-scoped call)
```
GET /api/v1/customers
Authorization: Bearer <access_token>
X-Tenant-Id: <tenant_id>
```

Notes
- Validation errors return the unified error envelope:
  `{ "error": { "code", "message", "details" }, "request_id": "<uuid>" }`
- Use `/healthz` and `/readyz` for health/readiness checks.
