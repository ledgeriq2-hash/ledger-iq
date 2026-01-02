from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_insight import AiInsight
from app.models.ai_run import AiRun
from app.models.expense import Expense
from app.models.invoice import Invoice, InvoiceStatus
from app.models.treasury_transaction import TreasuryTransaction


SEVERITY_ORDER = {"danger": 0, "warning": 1, "info": 2}


def _now() -> datetime:
    return datetime.now(UTC)


def _clamp_decimal(value: Decimal, *, min_value: Decimal, max_value: Decimal) -> Decimal:
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


async def _sum_treasury(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    from_dt: datetime,
    to_dt: datetime,
    direction: str,
) -> Decimal:
    result = await session.execute(
        select(func.coalesce(func.sum(TreasuryTransaction.amount), 0)).where(
            TreasuryTransaction.tenant_id == tenant_id,
            TreasuryTransaction.direction == direction,
            TreasuryTransaction.created_at >= from_dt,
            TreasuryTransaction.created_at < to_dt,
        )
    )
    return _to_decimal(result.scalar_one() or 0).quantize(Decimal("0.01"))


async def _sum_expenses(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    from_dt: datetime,
    to_dt: datetime,
) -> Decimal:
    result = await session.execute(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.tenant_id == tenant_id,
            Expense.created_at >= from_dt,
            Expense.created_at < to_dt,
        )
    )
    return _to_decimal(result.scalar_one() or 0).quantize(Decimal("0.01"))


async def _count_overdue_invoices(session: AsyncSession, *, tenant_id: UUID) -> int:
    result = await session.execute(
        select(func.count()).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status == InvoiceStatus.OVERDUE,
        )
    )
    return int(result.scalar_one() or 0)


async def list_insights(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    from_date: date | None = None,
    to_date: date | None = None,
    severity: str | None = None,
    min_confidence: Decimal | None = None,
    type: str | None = None,
    limit: int = 200,
) -> list[AiInsight]:
    clauses = [AiInsight.tenant_id == tenant_id]
    if from_date:
        clauses.append(func.date(AiInsight.created_at) >= from_date)
    if to_date:
        clauses.append(func.date(AiInsight.created_at) <= to_date)
    if severity:
        clauses.append(AiInsight.severity == str(severity))
    if type:
        clauses.append(AiInsight.type == str(type))
    if min_confidence is not None:
        clauses.append(AiInsight.confidence >= Decimal(str(min_confidence)))

    query = select(AiInsight).where(and_(*clauses)).order_by(AiInsight.created_at.desc()).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


async def get_top_insights(session: AsyncSession, *, tenant_id: UUID, limit: int = 3) -> list[AiInsight]:
    result = await session.execute(
        select(AiInsight)
        .where(AiInsight.tenant_id == tenant_id)
        .order_by(AiInsight.created_at.desc())
        .limit(200)
    )
    insights = list(result.scalars().all())

    def sort_key(i: AiInsight):
        return (
            SEVERITY_ORDER.get(str(i.severity).lower(), 99),
            -float(i.confidence or 0),
            i.created_at,
        )

    insights.sort(key=sort_key)
    return insights[:limit]


async def run_ai(session: AsyncSession, *, tenant_id: UUID) -> tuple[AiRun, list[AiInsight]]:
    started = _now()
    run = AiRun(
        tenant_id=tenant_id,
        status="RUNNING",
        started_at=started,
        finished_at=None,
        error=None,
    )
    session.add(run)
    await session.flush()

    insights: list[AiInsight] = []
    try:
        now = started

        week = timedelta(days=7)
        out_7 = await _sum_treasury(session, tenant_id=tenant_id, from_dt=now - week, to_dt=now, direction="out")
        out_prev_7 = await _sum_treasury(
            session, tenant_id=tenant_id, from_dt=now - (week * 2), to_dt=now - week, direction="out"
        )
        if out_prev_7 > 0:
            ratio = (out_7 / out_prev_7).quantize(Decimal("0.01"))
            if ratio >= Decimal("1.50"):
                confidence = _clamp_decimal(Decimal("0.75") + (ratio - Decimal("1.50")) * Decimal("0.10"), min_value=Decimal("0.50"), max_value=Decimal("0.95"))
                insights.append(
                    AiInsight(
                        tenant_id=tenant_id,
                        run_id=run.id,
                        type="treasury_outflow_spike",
                        severity="warning",
                        confidence=confidence.quantize(Decimal("0.01")),
                        title="Treasury outflow spike",
                        message=f"Outflows in the last 7 days increased to {out_7} vs {out_prev_7} in the prior 7 days.",
                        explanation="Heuristic: compares last 7 days vs previous 7 days treasury 'out' totals. AI does not modify any financial records.",
                        reference_type="treasury",
                        reference_id=None,
                    )
                )

        exp_30 = await _sum_expenses(session, tenant_id=tenant_id, from_dt=now - timedelta(days=30), to_dt=now)
        exp_prev_30 = await _sum_expenses(
            session, tenant_id=tenant_id, from_dt=now - timedelta(days=60), to_dt=now - timedelta(days=30)
        )
        if exp_prev_30 > 0:
            ratio = (exp_30 / exp_prev_30).quantize(Decimal("0.01"))
            if ratio >= Decimal("1.40"):
                confidence = _clamp_decimal(Decimal("0.70") + (ratio - Decimal("1.40")) * Decimal("0.10"), min_value=Decimal("0.50"), max_value=Decimal("0.95"))
                insights.append(
                    AiInsight(
                        tenant_id=tenant_id,
                        run_id=run.id,
                        type="expense_spike",
                        severity="warning",
                        confidence=confidence.quantize(Decimal("0.01")),
                        title="Expenses increased",
                        message=f"Expenses in the last 30 days are {exp_30} vs {exp_prev_30} in the previous 30 days.",
                        explanation="Heuristic: compares last 30 days vs previous 30 days expense totals. AI does not modify any financial records.",
                        reference_type="expense",
                        reference_id=None,
                    )
                )

        overdue_count = await _count_overdue_invoices(session, tenant_id=tenant_id)
        if overdue_count > 0:
            confidence = _clamp_decimal(Decimal("0.85"), min_value=Decimal("0.50"), max_value=Decimal("0.95"))
            insights.append(
                AiInsight(
                    tenant_id=tenant_id,
                    run_id=run.id,
                    type="overdue_invoices",
                    severity="danger",
                    confidence=confidence.quantize(Decimal("0.01")),
                    title="Overdue invoices",
                    message=f"There are {overdue_count} overdue invoices.",
                    explanation="Heuristic: counts invoices with status OVERDUE. AI does not modify any financial records.",
                    reference_type="invoice",
                    reference_id=None,
                )
            )

        if not insights:
            insights.append(
                AiInsight(
                    tenant_id=tenant_id,
                    run_id=run.id,
                    type="no_findings",
                    severity="info",
                    confidence=Decimal("0.60"),
                    title="No critical findings",
                    message="No high-severity heuristics triggered in this run.",
                    explanation="Heuristic set is minimal in MVP and only reads financial data.",
                    reference_type=None,
                    reference_id=None,
                )
            )

        for insight in insights:
            session.add(insight)

        run.status = "SUCCESS"
        run.finished_at = _now()
        await session.commit()
        for insight in insights:
            await session.refresh(insight)
        await session.refresh(run)
        return run, insights
    except Exception as exc:
        run.status = "FAILED"
        run.finished_at = _now()
        run.error = str(exc)[:500]
        await session.commit()
        await session.refresh(run)
        return run, []


async def list_runs(session: AsyncSession, *, tenant_id: UUID, limit: int = 200) -> list[AiRun]:
    result = await session.execute(
        select(AiRun)
        .where(AiRun.tenant_id == tenant_id)
        .order_by(AiRun.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


__all__ = ["list_insights", "get_top_insights", "run_ai", "list_runs"]
