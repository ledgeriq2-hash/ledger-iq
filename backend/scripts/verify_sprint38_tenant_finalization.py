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
        return response.status, dict(response.getheaders()), payload
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


def _parse_json(body: bytes, label: str) -> dict:
    try:
        return json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise VerificationError(f"{label}: invalid JSON response") from exc


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def _login_for_tenant(tenant_id: str, slug: str | None) -> str:
    if not slug:
        raise VerificationError("Cannot infer admin login email without tenant slug")
    email = f"admin-{slug}@example.com"
    password = os.environ.get("LEDGERIQ_BOOTSTRAP_PASSWORD", "Test1234")
    payload = {"email": email, "password": password}
    status, _, body = _request(
        "POST",
        "/api/v1/auth/login",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Tenant-Id": tenant_id,
        },
        body=json.dumps(payload).encode("utf-8"),
    )
    if status != 200:
        raise VerificationError(
            f"auth login failed: {status}: {body.decode('utf-8', errors='ignore')}"
        )
    response = _parse_json(body, "auth_login")
    access_token = (response.get("tokens") or {}).get("access_token")
    if not access_token:
        raise VerificationError("auth login missing access_token")
    return access_token


def run() -> None:
    _wait_for("/healthz", 200)
    _wait_for("/readyz", 200)

    status, _, body = _request("GET", "/api/v1/dev/tenants", headers={"Accept": "application/json"})
    if status == 403:
        raise VerificationError(
            "Dev tenants endpoint blocked. Set LEDGERIQ_ALLOW_DEV_ENDPOINTS=1 (or APP_ENV=dev) and retry."
        )
    if status != 200:
        raise VerificationError(f"tenants endpoint failed: {status}: {body.decode('utf-8', errors='ignore')}")

    data = _parse_json(body, "tenants")
    items = data.get("items") or []
    if not isinstance(items, list):
        raise VerificationError("tenants endpoint did not return an items list")

    tenant_count = len(items)
    access_token = None

    if tenant_count == 0:
        suffix = str(int(time.time()))
        payload = {
            "seed_demo": True,
            "tenant": {"name": f"Demo Company {suffix}", "slug": f"demo-{suffix}"},
            "admin": {"email": f"admin-{suffix}@example.com", "password": "Test1234", "full_name": "Demo Admin"},
        }
        status, _, body = _request(
            "POST",
            "/api/v1/dev/bootstrap",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            body=json.dumps(payload).encode("utf-8"),
        )
        if status != 201:
            raise VerificationError(
                f"bootstrap failed: {status}: {body.decode('utf-8', errors='ignore')}"
            )
        response = _parse_json(body, "bootstrap")
        tenant_id = response.get("tenant_id") or (response.get("tenant") or {}).get("id")
        access_token = response.get("access_token") or (response.get("tokens") or {}).get("access_token")
        if not tenant_id or not access_token:
            raise VerificationError("bootstrap response missing tenant_id or access_token")
        status, _, body = _request("GET", "/api/v1/dev/tenants", headers={"Accept": "application/json"})
        if status != 200:
            raise VerificationError(
                f"tenants re-fetch failed: {status}: {body.decode('utf-8', errors='ignore')}"
            )
        data = _parse_json(body, "tenants_refetch")
        items = data.get("items") or []
        if not isinstance(items, list):
            raise VerificationError("tenants re-fetch did not return an items list")
        tenant_count = len(items)
    else:
        tenant = items[0] or {}
        tenant_id = tenant.get("id")
        if not tenant_id:
            raise VerificationError("tenants endpoint missing tenant id")
        slug = tenant.get("slug") or ""
        access_token = _login_for_tenant(tenant_id, slug)

    target_path = "/api/v1/accounts/"
    status, _, body = _request("GET", target_path, headers=_auth_headers(access_token))

    if tenant_count == 1:
        if status != 200:
            raise VerificationError(
                f"expected 200 for single-tenant inference; got {status}: {body.decode('utf-8', errors='ignore')}"
            )
        _parse_json(body, "single_tenant_response")
        print("PASS: single-tenant inference OK")
    else:
        if status != 400:
            raise VerificationError(
                f"expected 400 for multi-tenant missing header; got {status}: {body.decode('utf-8', errors='ignore')}"
            )
        payload = _parse_json(body, "multi_tenant_error")
        code = payload.get("error", {}).get("code")
        if code != "TENANT_REQUIRED":
            raise VerificationError(f"expected TENANT_REQUIRED code, got {code!r}")
        print("PASS: multi-tenant TENANT_REQUIRED enforced")

    print("PASS: Sprint 38 tenant finalization gate")


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
