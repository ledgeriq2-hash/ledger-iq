# Sprint 28 Report — Production Security + Ops Hardening

Summary
- Added security headers middleware with HSTS in production only.
- Hardened CORS configuration via `CORS_ORIGINS` with safe local defaults in dev.
- Added production checklist documentation and a security headers verifier.

How to run verifier
```powershell
python backend/scripts/verify_sprint28_security_headers.py
```

Prod-mode verifier (requires backend running with `ENVIRONMENT=production`)
```powershell
$env:ENV = "prod"
python backend/scripts/verify_sprint28_security_headers.py
```

Files changed
- backend/app/core/settings.py
- backend/app/middleware/security_headers.py
- backend/app/middleware/__init__.py
- backend/app/main.py
- backend/scripts/verify_sprint28_security_headers.py
- docs/production_checklist.md
- sprint28_report.md
