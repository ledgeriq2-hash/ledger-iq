# Sprint 31 Report — Unified Release Gate

Summary
- Added a single release-gate verifier that runs health checks and Sprint 26/28/29/30 HTTP verifiers in sequence.
- Optionally runs frontend lint/build via docker compose when Docker is available.

How to run
```powershell
docker compose up -d
python backend/scripts/verify_release_gate.py
```

Optional cleanup
```powershell
docker compose down
```

Files changed
- backend/scripts/verify_release_gate.py
- sprint31_report.md
