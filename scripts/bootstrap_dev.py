from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _candidate_env_paths() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[1]
    backend_dir = repo_root / "backend"
    candidates: list[Path] = []
    for base in (backend_dir, repo_root):
        for name in (".env.local", ".env.development", ".env"):
            candidate = base / name
            if candidate.exists():
                candidates.append(candidate)
    return candidates


def _load_env_with_dotenv() -> bool:
    try:
        from dotenv import load_dotenv
    except Exception:
        return False
    loaded = False
    for path in _candidate_env_paths():
        if load_dotenv(dotenv_path=path, override=False):
            loaded = True
    return loaded


def _load_env_fallback() -> bool:
    loaded = False
    for path in _candidate_env_paths():
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, _, value = raw.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)
                loaded = True
    return loaded


def _prepare_environment() -> None:
    loaded = _load_env_with_dotenv()
    if not loaded and not _load_env_fallback():
        print("bootstrap_dev: env file not loaded; relying on process environment")

    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("CSRF_ENABLED", "false")
    os.environ.setdefault("BILLING_ENABLED", "false")
    os.environ.setdefault("FEATURE_OPTIONAL_ROUTES", "true")
    os.environ.setdefault("JWT_SECRET_KEY", "dev-jwt-secret-key")
    os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "dev-jwt-refresh-secret-key")
    os.environ.setdefault("STRIPE_API_KEY", "sk_test_dummy")
    os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://ledgeriq:ledgeriq_password@localhost:5432/ledgeriq",
    )


def _run_step(label: str, command: list[str], cwd: Path) -> None:
    print(f"bootstrap_dev: {label}")
    subprocess.run(command, cwd=str(cwd), check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap Ledger IQ local development.")
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Run app.initial_data to seed default roles/accounts.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Create a demo tenant/user via app.management.demo_data (optional).",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    backend_dir = repo_root / "backend"
    if not backend_dir.exists():
        raise SystemExit("bootstrap_dev: backend directory not found")

    _prepare_environment()

    _run_step(
        "running migrations (python -m alembic upgrade head)",
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        backend_dir,
    )

    if args.seed:
        _run_step(
            "seeding defaults (python -m app.initial_data)",
            [sys.executable, "-m", "app.initial_data"],
            backend_dir,
        )

    if args.demo:
        os.environ.setdefault("DEMO_OWNER_PASSWORD", "Secret123!")
        _run_step(
            "seeding demo tenant (python -m app.management.demo_data)",
            [sys.executable, "-m", "app.management.demo_data"],
            backend_dir,
        )

    print("bootstrap_dev: done")


if __name__ == "__main__":
    main()
