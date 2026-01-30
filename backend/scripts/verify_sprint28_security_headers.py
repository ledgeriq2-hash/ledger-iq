from __future__ import annotations

import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class VerificationError(RuntimeError):
    pass


BASE_URL = os.environ.get("BACKEND_BASE_URL") or "http://127.0.0.1:8000"
IS_PROD_CHECK = os.environ.get("ENV", "").strip().lower() == "prod"


def _fetch(path: str, *, origin: str | None = None) -> tuple[int, dict[str, str]]:
    url = f"{BASE_URL.rstrip('/')}{path}"
    request = Request(url, method="GET")
    if origin:
        request.add_header("Origin", origin)
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}
    except HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}
    except URLError as exc:
        raise VerificationError(f"request failed: {exc}") from exc


def run() -> None:
    status, headers = _fetch("/healthz")
    if status != 200:
        raise VerificationError(f"/healthz returned {status}")

    required_headers = {
        "x-content-type-options",
        "x-frame-options",
        "referrer-policy",
        "permissions-policy",
    }
    missing = [name for name in required_headers if not headers.get(name)]
    if missing:
        raise VerificationError(f"missing security headers: {', '.join(missing)}")

    if IS_PROD_CHECK:
        if not headers.get("strict-transport-security"):
            raise VerificationError("missing Strict-Transport-Security header in prod check")

        _, cors_headers = _fetch("/healthz", origin="http://localhost:5173")
        allow_origin = cors_headers.get("access-control-allow-origin")
        if allow_origin == "*":
            raise VerificationError("CORS wildcard detected in prod check")

    print("PASS: Sprint 28 security headers")


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
