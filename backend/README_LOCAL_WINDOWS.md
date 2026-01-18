# Ledger IQ Local Windows Setup (No Docker)

This guide enables `python -m alembic upgrade head` and `python scripts/verify_sprint3.py`
to run locally on Windows without manual environment exports.

## 1) Create local env file
Copy the example file to `.env.local` in **either** location:
- `C:\Users\Elmodather\Ledger IQ\backend\.env.local` (preferred)
- `C:\Users\Elmodather\Ledger IQ\.env.local`

PowerShell:
```powershell
Set-Location "C:\Users\Elmodather\Ledger IQ\backend"
Copy-Item ".env.local.example" ".env.local"
```

## 2) Optional quick env check
```powershell
Set-Location "C:\Users\Elmodather\Ledger IQ\backend"
python -c "from app.config import get_settings; print(get_settings().database_url)"
```

## 3) Run migrations
```powershell
Set-Location "C:\Users\Elmodather\Ledger IQ\backend"
python -m alembic upgrade head
```

## 4) Run Sprint 3 verification
```powershell
Set-Location "C:\Users\Elmodather\Ledger IQ\backend"
python "scripts\verify_sprint3.py"
```

## 5) Run Sprint 4 verification
```powershell
Set-Location "C:\Users\Elmodather\Ledger IQ\backend"
python "scripts\verify_sprint4.py"
```

## 6) Run Sprint 5 verification
```powershell
Set-Location "C:\Users\Elmodather\Ledger IQ\backend"
python "scripts\verify_sprint5.py"
```

## Notes
- If both `.env.local` files exist, the backend file takes precedence.
- For debug, you can set `ALEMBIC_DEBUG_ENV=1` to print which env file loaded
  and the DB host (passwords are never printed).
