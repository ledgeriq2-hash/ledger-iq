from __future__ import annotations

import os
import subprocess
import sys
import time
from http.client import HTTPConnection
from pathlib import Path
from urllib.parse import urlparse


BASE_URL = os.environ.get("BACKEND_BASE_URL") or "http://localhost:8000"


class VerificationError(RuntimeError):
    pass


def _wait_for(path: str, expected: int, timeout_seconds: int = 60) -> None:
    parsed = urlparse(BASE_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    deadline = time.monotonic() + timeout_seconds
    last_status: int | None = None
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        conn = None
        try:
            conn = HTTPConnection(host, port, timeout=10)
            conn.request("GET", path)
            response = conn.getresponse()
            last_status = response.status
            response.read()
            if response.status == expected:
                return
        except Exception as exc:
            last_error = exc
        finally:
            if conn is not None:
                conn.close()
        time.sleep(1)
    if last_error:
        raise VerificationError(f"{path} failed: {last_error!r}")
    raise VerificationError(f"{path} returned {last_status}, expected {expected}")


def _run_step(label: str, script_path: Path) -> None:
    env = os.environ.copy()
    env.setdefault("BACKEND_BASE_URL", BASE_URL)
    result = subprocess.run(
        [sys.executable, str(script_path)],
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise VerificationError(f"{label} failed with exit code {result.returncode}")


def _docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _run_frontend_gate() -> None:
    if not _docker_available():
        print("SKIP: docker not available; skipping frontend lint/build gate")
        return
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "frontend", "sh", "-lc", "npm run lint && npm run build"],
        check=False,
    )
    if result.returncode != 0:
        raise VerificationError("frontend gate failed")


def run() -> None:
    print("Waiting for /healthz")
    _wait_for("/healthz", 200)
    print("Waiting for /readyz")
    _wait_for("/readyz", 200)

    backend_dir = Path(__file__).resolve().parents[1]
    steps = [
        ("Sprint 26 verifier", backend_dir / "scripts" / "verify_sprint26_production_readiness.py"),
        ("Sprint 28 verifier", backend_dir / "scripts" / "verify_sprint28_security_headers.py"),
        ("Sprint 29 verifier", backend_dir / "scripts" / "verify_sprint29_openapi_contract.py"),
        ("Sprint 30 verifier", backend_dir / "scripts" / "verify_sprint30_config_validation.py"),
    ]

    for label, path in steps:
        print(f"Running {label}")
        if not path.exists():
            raise VerificationError(f"{label} missing at {path}")
        _run_step(label, path)

    print("Running frontend gate (docker)")
    _run_frontend_gate()

    print("PASS: Release gate")


def main() -> int:
    try:
        run()
        return 0
    except VerificationError as exc:
        print(f"FAIL: {exc}")
        return 1
    except Exception as exc:
        print(f"FAIL: unexpected error: {exc!r}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
