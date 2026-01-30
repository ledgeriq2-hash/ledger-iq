from __future__ import annotations

import json
import os
import time
from http.client import HTTPConnection
from urllib.parse import urlparse
from urllib.error import URLError
from urllib.request import urlopen


class VerificationError(RuntimeError):
    pass


BASE_URL = os.environ.get("BACKEND_BASE_URL") or "http://localhost:8000"


def _fetch_openapi() -> dict:
    url = f"{BASE_URL.rstrip('/')}/openapi.json"
    print(f"Fetching {url}")
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    deadline = time.monotonic() + 60
    last_status: int | None = None
    last_exc: Exception | None = None
    payload: str | None = None

    while time.monotonic() < deadline:
        conn = None
        try:
            conn = HTTPConnection(host, port, timeout=10)
            conn.request("GET", path)
            response = conn.getresponse()
            last_status = response.status
            if 200 <= response.status < 300:
                payload = response.read().decode("utf-8")
                break
            response.read()
        except Exception as exc:
            last_exc = exc
        finally:
            if conn is not None:
                conn.close()
        time.sleep(1)

    if payload is None:
        proxy_present = {
            "HTTP_PROXY": bool(os.environ.get("HTTP_PROXY")),
            "HTTPS_PROXY": bool(os.environ.get("HTTPS_PROXY")),
            "NO_PROXY": bool(os.environ.get("NO_PROXY")),
        }
        print(f"Failed to fetch {url}")
        print(f"Proxy env present: {proxy_present}")
        if last_status is not None:
            raise VerificationError(f"failed to fetch openapi.json: status={last_status}")
        raise VerificationError(f"failed to fetch openapi.json: {last_exc!r}")
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise VerificationError("openapi.json is not valid JSON") from exc


def run() -> None:
    schema = _fetch_openapi()
    components = schema.get("components", {})
    schemas = components.get("schemas", {})
    if "ErrorEnvelope" not in schemas:
        raise VerificationError("ErrorEnvelope schema missing from components.schemas")

    paths = schema.get("paths", {})
    if "/healthz" not in paths:
        raise VerificationError("/healthz not present in OpenAPI paths")
    if "/readyz" not in paths:
        raise VerificationError("/readyz not present in OpenAPI paths")

    readyz_get = paths.get("/readyz", {}).get("get", {})
    responses = readyz_get.get("responses", {})
    if "503" not in responses:
        raise VerificationError("/readyz missing documented 503 response")

    print("PASS: Sprint 29 OpenAPI contract")


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
