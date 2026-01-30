from __future__ import annotations

import json
import os
import time
from http.client import HTTPConnection
from urllib.parse import urlparse


class VerificationError(RuntimeError):
    pass


BASE_URL = os.environ.get("BACKEND_BASE_URL") or "http://localhost:8000"


def _request(path: str) -> tuple[int, dict[str, str], bytes]:
    parsed = urlparse(BASE_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    conn = HTTPConnection(host, port, timeout=10)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        body = response.read()
        headers = {k.lower(): v for k, v in response.getheaders()}
        return response.status, headers, body
    finally:
        conn.close()


def _wait_for(path: str, expected: int, timeout_seconds: int = 60) -> tuple[int, dict[str, str], bytes]:
    deadline = time.monotonic() + timeout_seconds
    last_status: int | None = None
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            status, headers, body = _request(path)
            last_status = status
            if status == expected:
                return status, headers, body
        except Exception as exc:
            last_error = exc
        time.sleep(1)
    if last_error:
        raise VerificationError(f"{path} failed: {last_error!r}")
    raise VerificationError(f"{path} returned {last_status}, expected {expected}")


def _assert_request_id(headers: dict[str, str], label: str) -> str:
    request_id = headers.get("x-request-id")
    if not request_id:
        raise VerificationError(f"{label} missing X-Request-ID header")
    return request_id


def run() -> None:
    _, health_headers, _ = _wait_for("/healthz", 200)
    _assert_request_id(health_headers, "/healthz")

    _, ready_headers, _ = _wait_for("/readyz", 200)
    _assert_request_id(ready_headers, "/readyz")

    status, headers, body = _request("/api/v1/dev/trigger-500")
    if status == 403:
        raise VerificationError(
            "Dev 500 trigger blocked. Set LEDGERIQ_ALLOW_DEV_ENDPOINTS=1 (or APP_ENV=dev) and retry."
        )
    if status != 500:
        raise VerificationError(f"/api/v1/dev/trigger-500 expected 500, got {status}")

    request_id = _assert_request_id(headers, "/api/v1/dev/trigger-500")
    content_type = headers.get("content-type", "")
    if not content_type.lower().startswith("application/json"):
        raise VerificationError(f"500 response Content-Type is not application/json: {content_type}")

    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise VerificationError(f"500 response is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict) or "error" not in payload or "request_id" not in payload:
        raise VerificationError("500 response missing error envelope")

    error = payload.get("error") or {}
    if not isinstance(error, dict) or "code" not in error or "message" not in error:
        raise VerificationError("500 response error object missing code/message")

    if payload.get("request_id") and payload.get("request_id") != request_id:
        raise VerificationError("X-Request-ID does not match request_id in body")

    print("PASS: Sprint 33 stability gate")


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
