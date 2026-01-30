from __future__ import annotations

import os
import time
from http.client import HTTPConnection
from urllib.parse import urlparse


class VerificationError(RuntimeError):
    pass


BASE_URL = os.environ.get("BACKEND_BASE_URL") or "http://localhost:8000"


def _request(path: str, *, origin: str | None = None) -> tuple[int, dict[str, str]]:
    parsed = urlparse(BASE_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    target = path
    conn = HTTPConnection(host, port, timeout=10)
    headers = {}
    if origin:
        headers["Origin"] = origin
    try:
        conn.request("GET", target, headers=headers)
        response = conn.getresponse()
        status = response.status
        resp_headers = {k.lower(): v for k, v in response.getheaders()}
        response.read()
        return status, resp_headers
    finally:
        conn.close()


def _wait_for(path: str, expected: int) -> None:
    deadline = time.monotonic() + 60
    last_status: int | None = None
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            status, _ = _request(path)
            last_status = status
            if status == expected:
                return
        except Exception as exc:
            last_error = exc
        time.sleep(1)
    if last_error:
        raise VerificationError(f"{path} failed: {last_error!r}")
    raise VerificationError(f"{path} returned {last_status}, expected {expected}")


def _parse_cors_origins() -> list[str]:
    value = os.environ.get("CORS_ORIGINS") or os.environ.get("BACKEND_CORS_ORIGINS") or ""
    if not value:
        return []
    if value.startswith("["):
        try:
            import json

            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            return []
    return [part.strip() for part in value.split(",") if part.strip()]


def run() -> None:
    _wait_for("/healthz", 200)
    _wait_for("/readyz", 200)

    env = (os.environ.get("ENVIRONMENT") or "").strip().lower()
    cors_origins = _parse_cors_origins()
    if env == "production" and cors_origins:
        origin = cors_origins[0] if cors_origins[0] != "*" else "http://example.com"
        _, headers = _request("/healthz", origin=origin)
        allow_origin = headers.get("access-control-allow-origin")
        if allow_origin == "*":
            raise VerificationError("CORS wildcard detected in production mode")

    print("PASS: Sprint 30 config validation")


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
