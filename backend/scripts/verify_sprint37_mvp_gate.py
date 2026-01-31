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


def _auth_headers(token: str, tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
        "Accept": "application/json",
    }


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

    seeded = False
    tenant_id = None
    access_token = None

    if len(items) == 0:
        seeded = True
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
    else:
        tenant = items[0] or {}
        tenant_id = tenant.get("id")
        if not tenant_id:
            raise VerificationError("tenants endpoint missing tenant id")
        slug = tenant.get("slug") or ""
        if slug:
            email = f"admin-{slug}@example.com"
            login_payload = {"email": email, "password": os.environ.get("LEDGERIQ_BOOTSTRAP_PASSWORD", "Test1234")}
            status, _, body = _request(
                "POST",
                "/api/v1/auth/login",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Tenant-Id": tenant_id,
                },
                body=json.dumps(login_payload).encode("utf-8"),
            )
            if status == 200:
                response = _parse_json(body, "auth_login")
                access_token = (response.get("tokens") or {}).get("access_token")
        if not access_token:
            raise VerificationError(
                "Could not obtain access token for existing tenant. Reset the DB or bootstrap a demo tenant "
                "so this verifier can authenticate."
            )

    headers = _auth_headers(access_token, tenant_id)

    status, _, body = _request("GET", "/api/v1/customers/", headers=headers)
    if status != 200:
        raise VerificationError(f"customers list failed: {status}: {body.decode('utf-8', errors='ignore')}")
    customers = _parse_json(body, "customers").get("items") or []
    if seeded and len(customers) < 1:
        raise VerificationError("seed_demo expected at least 1 customer")

    status, _, body = _request("GET", "/api/v1/vendors/", headers=headers)
    if status != 200:
        raise VerificationError(f"vendors list failed: {status}: {body.decode('utf-8', errors='ignore')}")
    vendors = _parse_json(body, "vendors").get("items") or []
    if seeded and len(vendors) < 1:
        raise VerificationError("seed_demo expected at least 1 vendor")

    status, _, body = _request("GET", "/api/v1/products/", headers=headers)
    if status != 200:
        raise VerificationError(f"products list failed: {status}: {body.decode('utf-8', errors='ignore')}")
    products = _parse_json(body, "products").get("items") or []
    if seeded and len(products) < 1:
        raise VerificationError("seed_demo expected at least 1 product")

    status, _, body = _request("GET", "/api/v1/sales-invoices/", headers=headers)
    if status != 200:
        raise VerificationError(f"sales invoices list failed: {status}: {body.decode('utf-8', errors='ignore')}")
    invoices = _parse_json(body, "sales_invoices").get("items") or []
    if seeded and len(invoices) < 1:
        raise VerificationError("seed_demo expected at least 1 sales invoice")

    if not customers:
        raise VerificationError("no customers available to create a portal link")
    customer_id = customers[0].get("id")
    if not customer_id:
        raise VerificationError("customer id missing for portal link")

    portal_payload = {"client_id": customer_id, "expires_in_hours": 1}
    status, _, body = _request(
        "POST",
        "/api/v1/portal/link",
        headers={**headers, "Content-Type": "application/json"},
        body=json.dumps(portal_payload).encode("utf-8"),
    )
    if status != 201:
        raise VerificationError(
            f"portal link failed: {status}: {body.decode('utf-8', errors='ignore')}"
        )

    print("PASS: Sprint 37 MVP gate")
    print("Manual UI smoke:")
    print("- Open http://localhost:5173")
    print('- Run: localStorage.removeItem("tenant_id")')
    print('- If present from older builds: localStorage.removeItem("tenant_slug")')
    print("- Reload: if exactly one tenant exists, the app should auto-select and continue")
    print("- If zero tenants exist, use 'Create demo company' and verify demo data appears")


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
