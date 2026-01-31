from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from httpx import Client, Timeout


def _candidate_env_paths() -> list[Path]:
    backend_dir = Path(__file__).resolve().parents[1]
    repo_root = Path(__file__).resolve().parents[2]
    candidates = []
    for base in (repo_root, backend_dir):
        for name in (".env.local", ".env.development", ".env"):
            candidate = base / name
            if candidate.exists():
                candidates.append(candidate)
    return candidates


def _load_env_with_dotenv() -> bool:
    try:
        from dotenv import load_dotenv
    except Exception:
        return False
    loaded = False
    for path in _candidate_env_paths():
        if load_dotenv(dotenv_path=path, override=False):
            loaded = True
    return loaded


def _load_env_fallback() -> bool:
    loaded = False
    for path in _candidate_env_paths():
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, _, value = raw.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)
                loaded = True
    return loaded


def _running_in_docker() -> bool:
    return Path("/.dockerenv").exists() or os.environ.get("RUNNING_IN_DOCKER") == "1"


def _normalize_host(url: str, *, local_host: str, docker_host: str) -> str:
    parsed = urlparse(url)
    if _running_in_docker() and parsed.hostname in {"localhost", "127.0.0.1"}:
        hostname = docker_host
    elif not _running_in_docker() and parsed.hostname in {docker_host, "db", "postgres", "redis"}:
        hostname = local_host
    else:
        return url

    default_port = 6379 if parsed.scheme == "redis" else 5432
    netloc = parsed.netloc
    port = parsed.port or default_port
    if "@" in netloc:
        creds, _ = netloc.rsplit("@", 1)
        netloc = f"{creds}@{hostname}:{port}"
    else:
        netloc = f"{hostname}:{port}"
    return urlunparse(parsed._replace(netloc=netloc))


def _prepare_environment() -> None:
    loaded = _load_env_with_dotenv()
    if not loaded and not _load_env_fallback():
        print("verify_sprint26: env file not loaded; relying on process environment")
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("CSRF_ENABLED", "false")
    os.environ.setdefault("BILLING_ENABLED", "false")
    os.environ.setdefault("FEATURE_OPTIONAL_ROUTES", "true")
    os.environ.setdefault("JWT_SECRET_KEY", "dev-jwt-secret-key")
    os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "dev-jwt-refresh-secret-key")
    os.environ.setdefault("STRIPE_API_KEY", "sk_test_dummy")
    os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://ledgeriq:ledgeriq_password@localhost:5432/ledgeriq",
    )
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

    db_url = os.environ.get("DATABASE_URL", "")
    if db_url:
        os.environ["DATABASE_URL"] = _normalize_host(
            db_url, local_host="127.0.0.1", docker_host="postgres"
        )

    redis_url = os.environ.get("REDIS_URL", "")
    if redis_url:
        os.environ["REDIS_URL"] = _normalize_host(
            redis_url, local_host="127.0.0.1", docker_host="redis"
        )


_prepare_environment()


class VerificationError(RuntimeError):
    pass


START_TIME = time.monotonic()
API_BASE_URL = os.environ.get("BACKEND_BASE_URL") or "http://127.0.0.1:8000"


def _normalize_api_base_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        return url
    if _running_in_docker() and host in {"localhost", "127.0.0.1"}:
        host = "backend"
    elif not _running_in_docker() and host == "backend":
        host = "127.0.0.1"
    if parsed.port:
        netloc = f"{host}:{parsed.port}"
    else:
        netloc = host
    return urlunparse(parsed._replace(netloc=netloc))


API_BASE_URL = _normalize_api_base_url(API_BASE_URL)


def _log(message: str) -> None:
    elapsed = time.monotonic() - START_TIME
    timestamp = datetime.now(UTC).isoformat()
    print(f"[{timestamp}] (+{elapsed:05.1f}s) {message}")


def _auth_headers(token: str, tenant_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-Id": str(tenant_id)}


def _require_request_id(response, label: str) -> None:
    request_id = response.headers.get("X-Request-ID")
    if not request_id:
        raise VerificationError(f"missing X-Request-ID header for {label}")


def _assert_error_envelope(payload: dict, label: str) -> None:
    if not isinstance(payload, dict):
        raise VerificationError(f"{label}: error response is not a JSON object")
    if "error" not in payload or "request_id" not in payload:
        raise VerificationError(f"{label}: missing error envelope keys")
    error = payload.get("error")
    if not isinstance(error, dict):
        raise VerificationError(f"{label}: error is not an object")
    for key in ("code", "message", "details"):
        if key not in error:
            raise VerificationError(f"{label}: error.{key} missing")
    if not payload.get("request_id"):
        raise VerificationError(f"{label}: request_id missing in payload")


def _wait_for_http(client: Client, path: str, expected_status: int, *, label: str) -> None:
    deadline = time.monotonic() + 20
    last_error: str | None = None
    while time.monotonic() < deadline:
        try:
            response = client.get(path)
        except Exception as exc:
            last_error = repr(exc)
            time.sleep(1.0)
            continue
        if response.status_code == expected_status:
            _require_request_id(response, label)
            return
        last_error = f"{response.status_code}: {response.text}"
        time.sleep(1.0)
    raise VerificationError(f"{label} not ready after 20s. Last error: {last_error}")


def _register_tenant(client: Client) -> tuple[uuid.UUID, str]:
    suffix = uuid.uuid4().hex[:8]
    tenant_slug = f"sprint26-{suffix}"
    payload = {
        "tenant": {"name": f"Sprint 26 {suffix}", "slug": tenant_slug},
        "admin": {
            "email": f"admin-{tenant_slug}@example.com",
            "password": "Test1234",
            "full_name": "Sprint 26 Admin",
        },
    }
    headers = {"X-Tenant-Id": str(uuid.uuid4())}
    response = client.post("/api/v1/auth/register", headers=headers, json=payload)
    _require_request_id(response, "auth_register")
    if response.status_code != 201:
        raise VerificationError(f"auth register failed: {response.status_code}: {response.text}")
    data = response.json()
    tenant_id = data.get("tenant", {}).get("id")
    access_token = data.get("tokens", {}).get("access_token")
    if not tenant_id or not access_token:
        raise VerificationError("auth register response missing tenant id or access token")
    return uuid.UUID(tenant_id), access_token


def run() -> None:
    timeout = Timeout(connect=5.0, read=15.0, write=15.0, pool=5.0)
    with Client(base_url=API_BASE_URL, timeout=timeout) as client:
        _log("TEST 1: /healthz")
        _wait_for_http(client, "/healthz", 200, label="/healthz")

        _log("TEST 2: /readyz")
        _wait_for_http(client, "/readyz", 200, label="/readyz")

        _log("TEST 3: register tenant + admin")
        tenant_id, token = _register_tenant(client)
        headers = _auth_headers(token, tenant_id)

        _log("TEST 4: validation error envelope")
        bad_customer = client.post("/api/v1/customers/", headers=headers, json={})
        _require_request_id(bad_customer, "validation_error")
        if bad_customer.status_code != 422:
            raise VerificationError(
                f"customer create expected 422, got {bad_customer.status_code}: {bad_customer.text}"
            )
        _assert_error_envelope(bad_customer.json(), "validation_error")

        _log("TEST 5: create customer + portal link")
        customer = client.post(
            "/api/v1/customers/",
            headers=headers,
            json={"code": f"S26-CUST-{uuid.uuid4().hex[:6]}", "name": "Sprint 26 Customer"},
        )
        if customer.status_code != 201:
            raise VerificationError(f"customer create failed: {customer.status_code}: {customer.text}")
        customer_id = customer.json().get("id")
        if not customer_id:
            raise VerificationError("customer id missing")

        link = client.post(
            "/api/v1/portal/link",
            headers=headers,
            json={"client_id": customer_id, "expires_in_hours": 1},
        )
        if link.status_code != 201:
            raise VerificationError(f"portal link failed: {link.status_code}: {link.text}")
        url = link.json().get("url")
        if not url:
            raise VerificationError("portal link url missing")
        raw_token = url.rstrip("/").split("/")[-1]
        if not raw_token:
            raise VerificationError("portal raw token missing")

        _log("TEST 6: rate limit public portal summary")
        rate_limited = False
        attempts: list[dict[str, str | int | None]] = []
        summary_path = f"/api/v1/portal/{raw_token}/summary"
        for idx in range(1, 30):
            response = client.get(summary_path)
            _require_request_id(response, "portal_summary")
            attempts.append(
                {
                    "attempt": idx,
                    "status": response.status_code,
                    "retry_after": response.headers.get("Retry-After"),
                    "x_forwarded_for": response.request.headers.get("X-Forwarded-For"),
                }
            )
            if response.status_code == 429:
                rate_limited = True
                if response.headers.get("Retry-After") is None:
                    raise VerificationError("Retry-After header missing on 429")
                _assert_error_envelope(response.json(), "rate_limit")
                break
            if response.status_code != 200:
                raise VerificationError(
                    f"portal summary unexpected {response.status_code} on attempt {idx}: {response.text}"
                )

        if not rate_limited:
            print(f"Rate limit debug: path={summary_path}")
            print("Rate limit debug: attempts=", attempts)
            raise VerificationError("rate limit was not enforced on portal summary")

    _log("PASS: Sprint 26 production readiness")


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
