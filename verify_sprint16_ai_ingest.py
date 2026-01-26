from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID


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


def _is_placeholder(value: str) -> bool:
    raw = value.strip()
    if not raw:
        return True
    if raw.startswith("<") and raw.endswith(">"):
        return True
    return False


def _require_tenant_id() -> UUID:
    raw = os.environ.get("AI_TEST_TENANT_ID", "")
    if _is_placeholder(raw):
        raise VerificationError("AI_TEST_TENANT_ID is required and must be a valid UUID")
    try:
        return UUID(raw)
    except Exception as exc:
        raise VerificationError("AI_TEST_TENANT_ID must be a valid UUID") from exc


def _load_payload(data: Any) -> dict:
    if isinstance(data, dict) and isinstance(data.get("payload"), dict):
        return data["payload"]
    if isinstance(data, dict):
        return data
    raise VerificationError("Payload must be a JSON object")


BACKEND_ROOT = Path(__file__).resolve().parent / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

_prepare_environment()

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker  # noqa: E402

from app.database import engine  # noqa: E402
from app.schemas.ai_insights_v1 import (  # noqa: E402
    ExplainabilityBlock,
    ForecastBlock,
    InsightsBlock,
    RiskBlock,
)
from app.schemas.ai_runs_v1 import AiRunCreateRequest, AiRunMetaV1  # noqa: E402
from app.services import ai_insights_v1_service, ai_runs_service  # noqa: E402
from app.utils.ai_hashing import canonical_sha256  # noqa: E402


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


def _validate_payload(payload: dict) -> None:
    errors: list[str] = []
    _validate_block("forecast", payload.get("forecast"), ForecastBlock, errors)
    _validate_block("risk", payload.get("risk"), RiskBlock, errors)
    _validate_block("explainability", payload.get("explainability"), ExplainabilityBlock, errors)
    _validate_block("insights", payload.get("insights"), InsightsBlock, errors)
    if errors:
        raise VerificationError("Invalid payload: " + "; ".join(errors))


async def run() -> None:
    repo_root = Path(__file__).resolve().parent
    payload_path = repo_root / "notebooks" / "output" / "ai_run_payload_baseline.json"
    if not payload_path.exists():
        raise VerificationError(f"Missing payload file: {payload_path}")

    data = json.loads(payload_path.read_text(encoding="utf-8"))
    payload = _load_payload(data)
    _validate_payload(payload)

    tenant_id = _require_tenant_id()

    run_meta_data = dict(data.get("run_meta") or {})
    run_meta_data.setdefault("model_name", "colab-insights")
    run_meta_data.setdefault("model_version", "v1")
    run_meta_data.setdefault("dataset_fingerprint", data.get("payload_hash") or "external")
    run_meta_data.setdefault("created_at", datetime.now(UTC).isoformat())
    run_meta_data.setdefault("scenario", "baseline")
    run_meta_data["created_by"] = "verifier"

    req = AiRunCreateRequest(
        schema_version=data.get("schema_version") or "1.0",
        run_meta=AiRunMetaV1(**run_meta_data),
        payload=payload,
        signature=data.get("signature"),
    )

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        run = await ai_runs_service.create_run(db=session, client_id=tenant_id, req=req)
        if run.status != "approved":
            raise VerificationError("AI run status is not approved")
        if run.client_id != tenant_id:
            raise VerificationError("AI run tenant_id mismatch")
        if run.schema_version != "1.0":
            raise VerificationError("AI run schema_version mismatch")
        if not run.created_at:
            raise VerificationError("AI run created_at missing")
        if not run.payload_hash or len(run.payload_hash) != 64:
            raise VerificationError("AI run payload_hash invalid")
        expected_hash = canonical_sha256(payload)
        if run.payload_hash != expected_hash:
            raise VerificationError("AI run payload_hash mismatch")
        if run.payload_json != payload:
            raise VerificationError("AI run payload_json mismatch")

        fetched = await ai_runs_service.get_run(db=session, client_id=tenant_id, run_id=run.id)
        if fetched.id != run.id:
            raise VerificationError("AI run fetch mismatch")

        insights = await ai_insights_v1_service.get_insights(
            db=session,
            client_id=tenant_id,
            scenario=req.run_meta.scenario,
        )
        if not insights:
            raise VerificationError("Insights not returned for new run")
        if insights.run.id != run.id:
            raise VerificationError("Insights did not select the latest run")
        for key in ("forecast", "risk", "explainability", "insights"):
            if getattr(insights, key) is None:
                raise VerificationError(f"Insights missing block: {key}")

    print("OK")


if __name__ == "__main__":
    asyncio.run(run())
