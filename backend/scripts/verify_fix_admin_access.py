import os
import sys

import requests

BASE_URL = os.getenv("LEDGERIQ_API_BASE", "http://localhost:8000")
DEV_ALLOW = os.getenv("LEDGERIQ_ALLOW_DEV_ENDPOINTS")


def _ensure_dev_flag():
    if DEV_ALLOW != "1":
        print("LEDGERIQ_ALLOW_DEV_ENDPOINTS=1 is required for this verification.", file=sys.stderr)
        sys.exit(1)


def bootstrap_tenant():
    payload = {"seed_demo": True}
    resp = requests.post(f"{BASE_URL}/api/v1/dev/bootstrap", json=payload)
    if resp.status_code == 409:
        raise SystemExit("Tenant already exists; run this script against a clean dev database.")
    resp.raise_for_status()
    return resp.json()


def ensure_owner(tenant_id: str, token: str):
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
    }
    resp = requests.post(f"{BASE_URL}/api/v1/dev/ensure-owner", headers=headers)
    resp.raise_for_status()
    print("Ensure-owner response:", resp.json())


def call_admin(tenant_id: str, token: str):
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
    }
    resp = requests.get(f"{BASE_URL}/api/v1/admin/tenants/", headers=headers)
    resp.raise_for_status()
    print("Admin endpoint accessible:", resp.status_code)


if __name__ == "__main__":
    _ensure_dev_flag()
    data = bootstrap_tenant()
    tenant_id = data["tenant_id"]
    token = data["access_token"]
    ensure_owner(tenant_id, token)
    call_admin(tenant_id, token)
