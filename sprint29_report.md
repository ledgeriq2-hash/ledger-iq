# Sprint 29 Report — API Contract Hardening

Summary
- Documented ErrorObject/ErrorEnvelope schemas in OpenAPI and wired error responses to reference them.
- Added explicit OpenAPI metadata for `/healthz` and `/readyz`, including `X-Request-ID` response headers.
- Added auth flow documentation and an OpenAPI verifier.

How to run verifier
```powershell
python backend/scripts/verify_sprint29_openapi_contract.py
```

Files changed
- backend/app/shared/errors.py
- backend/app/shared/__init__.py
- backend/app/main.py
- docs/auth_flow.md
- backend/scripts/verify_sprint29_openapi_contract.py
- sprint29_report.md
