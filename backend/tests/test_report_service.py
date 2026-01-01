from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.chart_of_account import AccountType
from app.services import report_service


class _StubSession:
    async def execute(self, *_args, **_kwargs):
        raise AssertionError("execute should be stubbed in tests")


@pytest.mark.asyncio
async def test_income_statement(monkeypatch):
    tenant_id = uuid4()
    calls: list[dict] = []

    async def fake_agg(_session, _tenant, account_types=None, **kwargs):
        calls.append({"account_types": account_types, "kwargs": kwargs})
        if account_types == [AccountType.REVENUE]:
            return [
                {"account_id": uuid4(), "debit": Decimal("0"), "credit": Decimal("120.00"), "name": "Sales", "code": "4000", "type": AccountType.REVENUE}
            ]
        if account_types == [AccountType.EXPENSE]:
            return [
                {"account_id": uuid4(), "debit": Decimal("30.00"), "credit": Decimal("0"), "name": "COGS", "code": "5000", "type": AccountType.EXPENSE}
            ]
        return []

    monkeypatch.setattr(report_service, "_account_aggregates", fake_agg)
    result = await report_service.get_income_statement(
        _StubSession(), tenant_id, from_date=date(2024, 1, 1), to_date=date(2024, 1, 31)
    )

    assert result["totals"]["revenue"] == Decimal("120.00")
    assert result["totals"]["expense"] == Decimal("30.00")
    assert result["net_income"] == Decimal("90.00")
    assert any(call["kwargs"]["from_date"] == date(2024, 1, 1) for call in calls)
    assert any(call["kwargs"]["to_date"] == date(2024, 1, 31) for call in calls)


@pytest.mark.asyncio
async def test_balance_sheet(monkeypatch):
    tenant_id = uuid4()

    async def fake_agg(_session, _tenant, account_types=None, **_kwargs):
        if account_types == [AccountType.ASSET]:
            return [{"account_id": uuid4(), "code": "1000", "name": "Cash", "type": AccountType.ASSET, "debit": Decimal("500"), "credit": Decimal("0")}]
        if account_types == [AccountType.LIABILITY]:
            return [{"account_id": uuid4(), "code": "2000", "name": "AP", "type": AccountType.LIABILITY, "debit": Decimal("0"), "credit": Decimal("200")}]
        if account_types == [AccountType.EQUITY]:
            return [{"account_id": uuid4(), "code": "3000", "name": "Equity", "type": AccountType.EQUITY, "debit": Decimal("0"), "credit": Decimal("300")}]
        return []

    monkeypatch.setattr(report_service, "_account_aggregates", fake_agg)
    result = await report_service.get_balance_sheet(_StubSession(), tenant_id, as_of_date=date(2024, 1, 31))

    assert result["totals"]["assets"] == Decimal("500")
    assert result["totals"]["liabilities"] == Decimal("200")
    assert result["totals"]["equity"] == Decimal("300")
    assert result["totals"]["balance_check"] == Decimal("0")


@pytest.mark.asyncio
async def test_cashflow_statement(monkeypatch):
    tenant_id = uuid4()
    cash_id = uuid4()

    async def fake_load_cash(_session, _tenant):
        return [cash_id]

    async def fake_agg(_session, _tenant, account_types=None, account_ids=None, **_kwargs):
        assert account_ids == [cash_id]
        return [
            {"account_id": cash_id, "code": "1000", "name": "Cash", "type": AccountType.ASSET, "debit": Decimal("150"), "credit": Decimal("50")}
        ]

    monkeypatch.setattr(report_service, "_load_cash_accounts", fake_load_cash)
    monkeypatch.setattr(report_service, "_account_aggregates", fake_agg)

    result = await report_service.get_cashflow_statement(
        _StubSession(), tenant_id, from_date=date(2024, 1, 1), to_date=date(2024, 1, 31)
    )
    assert result["net_cash_flow"] == Decimal("100")
    assert result["accounts_used"] == [cash_id]
    assert result["cash_accounts"][0]["debit"] == Decimal("150")
    assert result["cash_accounts"][0]["credit"] == Decimal("50")


@pytest.mark.asyncio
async def test_trial_balance(monkeypatch):
    tenant_id = uuid4()

    async def fake_agg(_session, _tenant, **_kwargs):
        return [
            {"account_id": uuid4(), "code": "1000", "name": "Cash", "type": AccountType.ASSET, "debit": Decimal("200"), "credit": Decimal("0")},
            {"account_id": uuid4(), "code": "2000", "name": "AP", "type": AccountType.LIABILITY, "debit": Decimal("0"), "credit": Decimal("200")},
        ]

    monkeypatch.setattr(report_service, "_account_aggregates", fake_agg)
    result = await report_service.get_trial_balance(_StubSession(), tenant_id, as_of_date=date(2024, 1, 31))

    totals = result["totals"]
    assert totals["debit"] == totals["credit"] == Decimal("200")
    assert totals["difference"] == Decimal("0")
