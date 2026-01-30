from __future__ import annotations

import json
import os
import uuid
from http.client import HTTPConnection
from urllib.parse import urlparse


class VerificationError(RuntimeError):
    pass


BASE_URL = os.environ.get("BACKEND_BASE_URL") or "http://localhost:8000"


def _request(
    method: str,
    path: str,
    *,
    body: str | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str]]:
    parsed = urlparse(BASE_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    conn = HTTPConnection(host, port, timeout=10)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        response.read()
        return response.status, {k.lower(): v for k, v in response.getheaders()}
    finally:
        conn.close()


def _assert_request_id(status: int, headers: dict[str, str], label: str) -> None:
    if not headers.get("x-request-id"):
        print(f"{label} status={status}")
        print(f"{label} headers={headers}")
        raise VerificationError(f"missing X-Request-ID for {label}")


def run() -> None:
    health_status, health_headers = _request("GET", "/healthz")
    _assert_request_id(health_status, health_headers, "healthz")

    tenant_slug = f"s32-{uuid.uuid4().hex[:8]}"
    payload = {
        "tenant": {"name": f"Sprint 32 {tenant_slug}", "slug": tenant_slug},
        "admin": {
            "email": f"admin-{tenant_slug}@example.com",
            "password": "Test1234",
            "full_name": "Sprint 32 Admin",
        },
    }
    headers = {
        "Content-Type": "application/json",
        "X-Tenant-Id": str(uuid.uuid4()),
    }
    register_status, register_headers = _request(
        "POST",
        "/api/v1/auth/register",
        body=json.dumps(payload),
        headers=headers,
    )
    _assert_request_id(register_status, register_headers, "auth_register")

    print("PASS: Sprint 32 request-id headers")


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
