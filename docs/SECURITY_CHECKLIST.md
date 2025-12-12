# Security Checklist

- **Token safety**: Store JWTs in memory/localStorage only; never commit secrets. Portal tokens are single-purpose; treat as secrets and expire.
- **CORS**: Restrict `BACKEND_CORS_ORIGINS` to trusted domains in prod; avoid `*`.
- **Input validation**: FastAPI + Pydantic schemas enforce types; validate UUIDs and decimals; reject unknown fields (extra ignored).
- **Error handling**: Standard JSON errors `{success:false,error:{code,message},request_id}`; avoid leaking stack traces; request IDs logged.
- **Security headers**: Nginx adds X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy strict-origin-when-cross-origin, CSP default-src 'self', gzip enabled.
- **Rate limiting**: Auth/portal/feedback limits via Redis; ensure Redis reachable and per-tenant keys used.
- **Secrets management**: Use env vars; keep `.env*` out of git; inject via GitHub Secrets/host secrets; rotate JWT/Stripe/DB creds on incidents.
- **Authz**: Role checks on admin/billing; tenant isolation enforced via middleware; portal tokens validated by hash + expiry + type.
- **Data handling**: PII in logs avoided; structured JSON logging with correlation IDs; avoid logging secrets or payloads.
