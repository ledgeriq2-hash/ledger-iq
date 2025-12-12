from __future__ import annotations

import asyncio
from celery import shared_task

from app.database import async_session_maker
from app.services import recurring_invoice_service


@shared_task(name="app.tasks.recurring_tasks.run_due_recurring_invoices")
def run_due_recurring_invoices() -> dict:
    async def _run():
        async with async_session_maker() as session:
            generated = await recurring_invoice_service.process_due_recurring_invoices(session)
            return {"generated": len(generated), "invoice_ids": [str(i) for i in generated]}

    return asyncio.run(_run())


__all__ = ["run_due_recurring_invoices"]
