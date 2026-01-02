from __future__ import annotations

import asyncio
import json
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import delete, select

from app.config import get_settings
from app.database import async_session_maker
from app.models.customer import Customer
from app.models.employee import Employee
from app.models.feedback import Feedback
from app.models.gdpr_request import GdprRequest
from app.models.supplier import Supplier
from app.models.user import User


def _run_async(coro) -> None:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
        return

    error: list[BaseException] = []

    def _runner() -> None:
        try:
            asyncio.run(coro)
        except BaseException as exc:  # noqa: BLE001 - capture to re-raise on caller thread
            error.append(exc)

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if error:
        raise error[0]


async def _run_export_async(request_id: str) -> None:
    settings = get_settings()
    try:
        req_id = UUID(str(request_id))
    except ValueError:
        return

    async with async_session_maker() as session:
        req = await session.get(GdprRequest, req_id)
        if not req:
            return

        exports_dir = Path("gdpr_exports")
        exports_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{req.tenant_id}_{req.id}.json"
        artifact_path = exports_dir / filename

        payload = {
            "tenant_id": str(req.tenant_id),
            "request_id": str(req.id),
            "generated_at": datetime.now(UTC).isoformat(),
        }
        artifact_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

        req.status = "ready"
        req.artifact_path = str(artifact_path)
        req.expires_at = datetime.now(UTC) + timedelta(days=int(settings.gdpr_export_ttl_days or 0))
        await session.commit()


async def _run_delete_async(request_id: str) -> None:
    settings = get_settings()
    try:
        req_id = UUID(str(request_id))
    except ValueError:
        return

    async with async_session_maker() as session:
        req = await session.get(GdprRequest, req_id)
        if not req:
            return

        tenant_id = req.tenant_id
        retention_days = int(settings.gdpr_financial_retention_days or 0)

        if retention_days <= 0:
            await session.execute(delete(Feedback).where(Feedback.tenant_id == tenant_id))
            req.status = "deleted"
            req.delete_after = None
            await session.commit()
            return

        customers = (await session.execute(select(Customer).where(Customer.tenant_id == tenant_id))).scalars().all()
        for customer in customers:
            customer.name = "[GDPR_ANONYMIZED]"
            customer.email = None
            customer.phone = None
            customer.tax_id = None

        suppliers = (await session.execute(select(Supplier).where(Supplier.tenant_id == tenant_id))).scalars().all()
        for supplier in suppliers:
            supplier.name = "[GDPR_ANONYMIZED]"
            supplier.email = None
            supplier.phone = None
            supplier.address = None
            supplier.tax_id = None

        employees = (await session.execute(select(Employee).where(Employee.tenant_id == tenant_id))).scalars().all()
        for employee in employees:
            employee.name = "[GDPR_ANONYMIZED]"
            employee.email = None
            employee.phone = None
            employee.address = None
            employee.tax_id = None

        feedback_items = (await session.execute(select(Feedback).where(Feedback.tenant_id == tenant_id))).scalars().all()
        for item in feedback_items:
            item.message = "[GDPR_ANONYMIZED]"
            item.category = "[GDPR_ANONYMIZED]"

        users = (await session.execute(select(User).where(User.tenant_id == tenant_id))).scalars().all()
        for user in users:
            user.full_name = "[GDPR_ANONYMIZED]"
            user.email = f"gdpr-deleted-{uuid4()}@example.com"
            user.is_active = False

        req.status = "retention_pending"
        req.delete_after = datetime.now(UTC) + timedelta(days=retention_days)
        await session.commit()


def run_export(request_id: str) -> None:
    _run_async(_run_export_async(request_id))


def run_delete(request_id: str) -> None:
    _run_async(_run_delete_async(request_id))


run_export.delay = run_export  # type: ignore[attr-defined]
run_delete.delay = run_delete  # type: ignore[attr-defined]


__all__ = ["run_export", "run_delete"]
