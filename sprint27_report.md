# Sprint 27 Report — CI + Stability Gate

Summary
- Added a CI stability gate job that boots the Docker Compose stack, waits for readiness, runs the Sprint 26 HTTP verifier, and runs frontend lint/build in the container.
- Added a lightweight backend readiness script that checks container health plus `/healthz` and `/readyz`.
- Updated CI triggers to run on `main` and `wip/stabilization-split` for push and PRs.

Workflow triggers
- push: `main`, `wip/stabilization-split`
- pull_request: `main`, `wip/stabilization-split`
- workflow_dispatch

What it runs
1) `docker compose up -d --build`
2) `scripts/wait_for_backend_ready.sh` (checks container health + `/healthz` + `/readyz`)
3) `python backend/scripts/verify_sprint26_production_readiness.py`
4) `docker compose exec -T frontend sh -lc "npm run lint"`
5) `docker compose exec -T frontend sh -lc "npm run build"`
6) `docker compose logs` on failure
7) `docker compose down -v` always

How to run locally
```powershell
docker compose up -d --build
$env:CHECK_DOCKER_HEALTH = "1"
$env:BASE_URL = "http://localhost:8000"
scripts/wait_for_backend_ready.sh
python backend/scripts/verify_sprint26_production_readiness.py
docker compose exec -T frontend sh -lc "npm run lint"
docker compose exec -T frontend sh -lc "npm run build"
docker compose down -v
```

Files changed
- .github/workflows/ci.yml
- scripts/wait_for_backend_ready.sh
- sprint27_report.md
