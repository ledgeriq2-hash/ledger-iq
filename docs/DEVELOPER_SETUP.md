# Developer Setup

## Requirements
- Python 3.11+
- Node.js 20 + npm
- Docker / Docker Compose
- PostgreSQL & Redis locally (or use docker-compose)

## Local env
- Copy `.env.example` → `.env.development` (root) and export when running locally.
- Backend reads env vars; no implicit .env in production. `ENVIRONMENT=development` for local.

## Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
celery -A app.tasks.celery_app.celery_app worker --loglevel=info
celery -A app.tasks.celery_app.celery_app beat --loglevel=info  # for recurring invoices + scheduled jobs
```
Run migrations (if alembic present): `alembic upgrade head`.

## Frontend
```bash
cd frontend
npm ci
npm run dev
```
Vite uses `VITE_API_URL` (see env).

## Full stack via Docker
```bash
docker compose up --build
```
Services: db (5432), redis (6379), backend (8000), frontend (3000), prometheus (9090), grafana (3001).

## Testing
- Backend: `cd backend && pytest`
- Lint/type: `cd backend && ruff check app tests && mypy app`
- Frontend: `cd frontend && npm run lint && npm run test:e2e` (requires backend/front running or preview per CI).
- Load: `k6 run load_tests/smoke.js` (env `BASE_URL`, `TOKEN`, `TENANT_ID`).

## CI/CD
- GitHub Actions jobs: backend-tests, lint (ruff+mypy+eslint), frontend-tests, build (frontend bundle + backend/frontend Docker images), e2e-tests (Playwright), optional load-test-smoke (manual), deploy on tags.
- Push to `main`: tests + lint + build + e2e. Tags `v*.*.*`: build/push images to GHCR and optional SSH deploy (secrets required).
