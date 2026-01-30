from __future__ import annotations

import json
import os
import time
import uuid
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
        response_headers = {k.lower(): v for k, v in response.getheaders()}
        return response.status, response_headers, payload
    finally:
        conn.close()


def _wait_for(path: str, expected: int, timeout_seconds: int = 60) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = None
    while time.monotonic() < deadline:
        try:
            status, _, _ = _request("GET", path)
            if status == expected:
                return
            last_error = f"status={status}"
        except Exception as exc:
            last_error = repr(exc)
        time.sleep(1)
    raise VerificationError(f"{path} not ready after {timeout_seconds}s. Last error: {last_error}")


def _register_tenant() -> uuid.UUID:
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "tenant": {"name": f"Sprint 34 {suffix}", "slug": f"sprint34-{suffix}"},
        "admin": {
            "email": f"admin-sprint34-{suffix}@example.com",
            "password": "Test1234",
            "full_name": "Sprint 34 Admin",
        },
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Tenant-Id": str(uuid.uuid4()),
    }
    status, _, body = _request("POST", "/api/v1/auth/register", headers=headers, body=json.dumps(payload).encode("utf-8"))
    if status != 201:
        raise VerificationError(f"auth register failed: {status}: {body.decode('utf-8', errors='ignore')}")
    data = json.loads(body.decode("utf-8") or "{}")
    tenant_id = data.get("tenant", {}).get("id")
    if not tenant_id:
        raise VerificationError("auth register response missing tenant id")
    return uuid.UUID(tenant_id)


def run() -> None:
    _wait_for("/healthz", 200)
    _wait_for("/readyz", 200)

    _register_tenant()

    status, _, body = _request("GET", "/api/v1/dev/tenants")
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
    if len(items) != 1:
        raise VerificationError(
            f"expected exactly 1 tenant for auto-select flow, found {len(items)}"
        )

    print("PASS: Sprint 34 tenantless UX (API precheck)")
    print("Manual UI smoke:")
    print("- Open http://localhost:5173")
    print('- Run: localStorage.removeItem("tenant_id")')
    print('- If present from older versions: localStorage.removeItem("tenant_slug")')
    print("- Reload: app should skip tenant selector when only one tenant exists")


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
