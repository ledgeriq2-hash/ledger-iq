# Local Backend Dev (Canonical)

This is the single, end-to-end local backend flow (venv, env vars, migrations, seed, server, verifiers).

## 1) Create and activate the venv
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 2) Set local environment defaults
```powershell
# optional: create git-ignored env files for development
Copy-Item ..\.env.example ..\.env.local -Force
Copy-Item .\.env.example .\.env.local -Force

# required in local dev (can also be in .env.local)
$env:ENVIRONMENT = "development"
$env:DATABASE_URL = "postgresql+asyncpg://ledgeriq:ledgeriq_password@localhost:5432/ledgeriq"
```

## 3) Bootstrap: migrations + seed
```powershell
cd ..
python scripts/bootstrap_dev.py --seed
```

Optional demo tenant/user:
```powershell
python scripts/bootstrap_dev.py --demo
```

If you prefer running migrations manually from `backend/`:
```powershell
cd backend
python -m alembic upgrade head
python -m app.initial_data
```

## 4) Run the API
```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Health check: `http://localhost:8000/health`

## 5) Run verifiers (from repo root)
```powershell
cd ..
python verify_all.py
```
