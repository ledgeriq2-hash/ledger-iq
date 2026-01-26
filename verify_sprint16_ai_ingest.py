from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import types
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx


class VerificationError(RuntimeError):
    pass


def _candidate_env_paths() -> list[Path]:
    repo_root = Path(__file__).resolve().parent
    backend_dir = repo_root / "backend"
    candidates = []
    for base in (backend_dir, repo_root):
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


def _prepare_environment() -> None:
    loaded = _load_env_with_dotenv()
    if not loaded and not _load_env_fallback():
        print("verify_sprint16_ai_ingest: env file not loaded; relying on process environment")


def _is_placeholder(value: str) -> bool:
    raw = value.strip()
    if not raw:
        return True
    if raw.startswith("<") and raw.endswith(">"):
        return True
    return False


def _resolve_env(names: list[str]) -> tuple[str | None, str | None]:
    for name in names:
        value = os.environ.get(name, "")
        if value and not _is_placeholder(value):
            return value, name
    for name in names:
        value = os.environ.get(name, "")
        if value and _is_placeholder(value):
            raise VerificationError(f"{name} is still a placeholder")
    return None, None


def _require_uuid(value: str, name: str) -> None:
    try:
        UUID(value)
    except Exception as exc:
        raise VerificationError(f"{name} must be a valid UUID") from exc


def _ensure_pkg(name: str, path: Path) -> None:
    if name in sys.modules:
        return
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    module.__package__ = name
    sys.modules[name] = module


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module {module_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_schemas(repo_root: Path):
    backend_root = repo_root / "backend"
    app_path = backend_root / "app"
    schemas_path = app_path / "schemas"
    common_path = schemas_path / "common.py"
    insights_path = schemas_path / "ai_insights_v1.py"

    if not insights_path.exists():
        raise VerificationError(f"Missing schema file: {insights_path}")

    _ensure_pkg("app", app_path)
    _ensure_pkg("app.schemas", schemas_path)
    _load_module("app.schemas.common", common_path)
    module = _load_module("app.schemas.ai_insights_v1", insights_path)

    return (
        module.ExplainabilityBlock,
        module.ForecastBlock,
        module.InsightsBlock,
        module.RiskBlock,
    )


def _load_payload(data: Any) -> dict:
    if isinstance(data, dict) and isinstance(data.get("payload"), dict):
        return data["payload"]
    if isinstance(data, dict):
        return data
    raise VerificationError("Payload must be a JSON object")


def _validate_block(name: str, value: Any, schema_cls, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(f"{name}: expected object, got {type(value).__name__}")
        return
    try:
        schema_cls.model_validate(value)
    except Exception as exc:
        errors.append(f"{name}: {exc}")


def _validate_payload(payload: dict, schemas: tuple) -> None:
    explainability_cls, forecast_cls, insights_cls, risk_cls = schemas
    errors: list[str] = []
    _validate_block("forecast", payload.get("forecast"), forecast_cls, errors)
    _validate_block("risk", payload.get("risk"), risk_cls, errors)
    _validate_block("explainability", payload.get("explainability"), explainability_cls, errors)
    _validate_block("insights", payload.get("insights"), insights_cls, errors)
    if errors:
        raise VerificationError("Invalid payload: " + "; ".join(errors))


async def run() -> None:
    _prepare_environment()
    repo_root = Path(__file__).resolve().parent
    payload_path = repo_root / "notebooks" / "output" / "ai_run_payload_baseline.json"
    if not payload_path.exists():
        raise VerificationError(f"Missing payload file: {payload_path}")

    data = json.loads(payload_path.read_text(encoding="utf-8"))
    payload = _load_payload(data)

    schemas = _load_schemas(repo_root)
    _validate_payload(payload, schemas)

    base_url = (
        os.environ.get("AI_BASE_URL")
        or os.environ.get("BASE_URL")
        or os.environ.get("AI_TEST_BASE_URL")
        or "http://127.0.0.1:8000"
    ).rstrip("/")
    token, _ = _resolve_env(["AI_TEST_JWT", "TEST_JWT", "JWT"])
    tenant_id, tenant_name = _resolve_env(["AI_TEST_TENANT_ID"])
    missing: list[str] = []
    if not token:
        missing.append("AI_TEST_JWT (or TEST_JWT/JWT)")
    if not tenant_id:
        missing.append("AI_TEST_TENANT_ID")
    if missing:
        raise VerificationError("Missing required env vars: " + ", ".join(missing))
    _require_uuid(tenant_id, tenant_name or "AI_TEST_TENANT_ID")

    run_meta = data.get("run_meta") or {
        "model_name": "colab-insights",
        "model_version": "v1",
        "dataset_fingerprint": data.get("payload_hash") or "external",
        "created_at": datetime.now(UTC).isoformat(),
        "scenario": "baseline",
    }
    body = {
        "schema_version": data.get("schema_version") or "1.0",
        "run_meta": run_meta,
        "payload": payload,
        "signature": data.get("signature"),
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
    }

    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        resp = await client.post("/api/v1/ai/runs", headers=headers, json=body)
        if resp.status_code != 201:
            raise VerificationError(f"POST /ai/runs failed: {resp.status_code} {resp.text}")
        created = resp.json()
        if created.get("status") != "approved":
            raise VerificationError("AI run status is not approved")

        insights_resp = await client.get(
            "/api/v1/ai/insights-v1",
            headers=headers,
            params={"scenario": run_meta.get("scenario") or "baseline"},
        )
        if insights_resp.status_code != 200:
            raise VerificationError(
                f"GET /ai/insights-v1 failed: {insights_resp.status_code} {insights_resp.text}"
            )
        insights = insights_resp.json()
        if not insights.get("run"):
            raise VerificationError("Insights response missing run metadata")
        for key in ("forecast", "risk", "explainability", "insights"):
            if not insights.get(key):
                raise VerificationError(f"Insights response missing block: {key}")

    print("OK")


if __name__ == "__main__":
    asyncio.run(run())
