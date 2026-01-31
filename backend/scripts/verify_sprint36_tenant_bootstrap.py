from __future__ import annotations

import json
import os
import time
from http.client import HTTPConnection, HTTPSConnection
from urllib.parse import urlparse


class VerificationError(RuntimeError):
    pass


BASE_URL = os.environ.get("BACKEND_BASE_URL") or "http://localhost:8000"


def _connection():
    parsed = urlparse(BASE_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    conn_cls = HTTPSConnection if parsed.scheme == "https" else HTTPConnection
    return conn_cls(host, port, timeout=10), parsed


def _full_path(parsed, path: str) -> str:
    target = path if path.startswith("/") else f"/{path}"
    base_path = parsed.path.rstrip("/")
    if base_path:
        target = f"{base_path}{target}"
    if parsed.query:
        target = f"{target}?{parsed.query}"
    return target


def _request(method: str, path: str, headers: dict | None = None, body: bytes | None = None):
    conn, parsed = _connection()
    try:
        conn.request(method, _full_path(parsed, path), body=body, headers=headers or {})
        response = conn.getresponse()
        payload = response.read()
        return response.status, payload
    finally:
        conn.close()


def _wait_for(path: str, expected: int, timeout_seconds: int = 60) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = None
    while time.monotonic() < deadline:
        try:
            status, _ = _request("GET", path)
            if status == expected:
                return
            last_error = f"status={status}"
        except Exception as exc:
            last_error = repr(exc)
        time.sleep(1)
    raise VerificationError(f"{path} not ready after {timeout_seconds}s. Last error: {last_error}")


def run() -> None:
    _wait_for("/healthz", 200)
    _wait_for("/readyz", 200)

    status, body = _request("GET", "/api/v1/dev/tenants")
    if status == 403:
        raise VerificationError(
            "Dev tenants endpoint blocked. Set LEDGERIQ_ALLOW_DEV_ENDPOINTS=1 (or APP_ENV=dev) and retry."
        )
    if status != 200:
        raise VerificationError(f"tenants endpoint failed: {status}: {body.decode('utf-8', errors='ignore')}")

    data = json.loads(body.decode("utf-8") or "{}")
    items = data.get("items") or []
    if not isinstance(items, list):
        raise VerificationError("tenants endpoint did not return an items list")

    if len(items) == 0:
        suffix = str(int(time.time()))
        payload = {
            "tenant": {"name": f"Demo Company {suffix}", "slug": f"demo-{suffix}"},
            "admin": {"email": f"admin-{suffix}@example.com", "password": "Test1234", "full_name": "Demo Admin"},
        }
        status, body = _request(
            "POST",
            "/api/v1/dev/bootstrap",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            body=json.dumps(payload).encode("utf-8"),
        )
        if status != 201:
            raise VerificationError(
                f"bootstrap failed: {status}: {body.decode('utf-8', errors='ignore')}"
            )

        status, body = _request("GET", "/api/v1/dev/tenants")
        if status != 200:
            raise VerificationError(f"tenants endpoint failed after bootstrap: {status}")
        data = json.loads(body.decode("utf-8") or "{}")
        items = data.get("items") or []
        if not isinstance(items, list) or len(items) == 0:
            raise VerificationError("bootstrap did not create a tenant")

    print("PASS: Sprint 36 tenant bootstrap precheck")
    print("Manual UI smoke:")
    print("- Open http://localhost:5173")
    print('- Run: localStorage.removeItem("tenant_id")')
    print('- If present from older builds: localStorage.removeItem("tenant_slug")')
    print("- Reload: if exactly one tenant exists, the app should auto-select and continue")
    print("- If zero tenants exist, use 'Create demo company' and verify tenant_id is set")


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
