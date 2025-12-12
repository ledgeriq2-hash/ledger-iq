from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session_maker
from app.models.chart_of_account import AccountType, ChartOfAccount
from app.models.journal_entry_line import JournalEntryLine
from app.models.tenant import Tenant


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_accounts(session, tenant_id: UUID) -> dict[str, UUID]:
    accounts = {
        "cash": ChartOfAccount(code="1000", name="Cash", type=AccountType.ASSET, tenant_id=tenant_id),
        "ar": ChartOfAccount(code="1100", name="A/R", type=AccountType.ASSET, tenant_id=tenant_id),
        "revenue": ChartOfAccount(code="4000", name="Revenue", type=AccountType.REVENUE, tenant_id=tenant_id),
        "expense": ChartOfAccount(code="5000", name="Expense", type=AccountType.EXPENSE, tenant_id=tenant_id),
        "ap": ChartOfAccount(code="2000", name="A/P", type=AccountType.LIABILITY, tenant_id=tenant_id),
    }
    session.add_all(accounts.values())
    await session.commit()
    for name, acct in accounts.items():
        await session.refresh(acct)
        accounts[name] = acct.id
    return accounts  # type: ignore[return-value]


async def _apply_mapping(session, tenant_id: UUID, mapping: dict[str, UUID]) -> None:
    tenant = (await session.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    tenant.settings_json = {
        "chart_of_accounts_mapping": {
            "accounts_receivable_account_id": str(mapping["ar"]),
            "revenue_account_id": str(mapping["revenue"]),
            "expense_account_id": str(mapping["expense"]),
            "cash_account_id": str(mapping["cash"]),
            "payables_account_id": str(mapping["ap"]),
            "cashflow_account_ids": [str(mapping["cash"])],
        }
    }
    await session.commit()


async def _count_lines(session, tenant_id: UUID, account_id: UUID, debit: bool = True) -> Decimal:
    result = await session.execute(
        select(JournalEntryLine).where(
            JournalEntryLine.tenant_id == tenant_id,
            JournalEntryLine.account_id == account_id,
        )
    )
    amount = Decimal("0")
    for line in result.scalars().all():
        amount += line.debit if debit else line.credit
    return amount


@pytest.mark.anyio
async def test_invoice_payment_expense_journals_use_mapping(client: AsyncClient, register_owner):
    owner = await register_owner()
    token = owner["tokens"]["access_token"]
    tenant_id = UUID(owner["tenant"]["id"])

    async with async_session_maker() as session:
        accounts = await _create_accounts(session, tenant_id)
        await _apply_mapping(session, tenant_id, accounts)

    cust_res = await client.post(
        "/api/v1/customers/",
        json={"name": "ACME", "email": "acme@example.com"},
        headers=auth_headers(token),
    )
    assert cust_res.status_code == 201, cust_res.text
    customer = cust_res.json()

    inv_res = await client.post(
        "/api/v1/invoices/",
        json={
            "customer_id": customer["id"],
            "issue_date": date.today().isoformat(),
            "due_date": date.today().isoformat(),
            "status": "PAID",
            "currency": "USD",
            "items": [{"description": "Service", "quantity": "1", "unit_price": "100.00", "tax_rate": "0"}],
        },
        headers=auth_headers(token),
    )
    assert inv_res.status_code == 201, inv_res.text

    pay_res = await client.post(
        "/api/v1/payments/",
        json={
            "customer_id": customer["id"],
            "amount": "50.00",
            "method": "bank",
            "invoice_id": inv_res.json()["id"],
        },
        headers=auth_headers(token),
    )
    assert pay_res.status_code == 201, pay_res.text

    supplier_res = await client.post(
        "/api/v1/suppliers/",
        json={"name": "Vendor", "email": "vendor@example.com", "phone": "555-1234"},
        headers=auth_headers(token),
    )
    assert supplier_res.status_code == 201, supplier_res.text
    supplier = supplier_res.json()

    exp_res = await client.post(
        "/api/v1/expenses/",
        json={
            "supplier_id": supplier["id"],
            "category": "Ops",
            "amount": "30.00",
            "currency": "USD",
            "expense_date": date.today().isoformat(),
            "description": "Supplies",
        },
        headers=auth_headers(token),
    )
    assert exp_res.status_code == 201, exp_res.text

    async with async_session_maker() as session:
        ar_debit = await _count_lines(session, tenant_id, accounts["ar"], debit=True)
        revenue_credit = await _count_lines(session, tenant_id, accounts["revenue"], debit=False)
        cash_debit = await _count_lines(session, tenant_id, accounts["cash"], debit=True)
        ar_credit = await _count_lines(session, tenant_id, accounts["ar"], debit=False)
        expense_debit = await _count_lines(session, tenant_id, accounts["expense"], debit=True)
        ap_credit = await _count_lines(session, tenant_id, accounts["ap"], debit=False)

    assert ar_debit >= Decimal("100.00")
    assert revenue_credit >= Decimal("100.00")
    assert cash_debit >= Decimal("50.00")
    assert ar_credit >= Decimal("50.00")
    assert expense_debit >= Decimal("30.00")
    assert ap_credit >= Decimal("30.00")


@pytest.mark.anyio
async def test_missing_mapping_is_graceful(client: AsyncClient, register_owner):
    owner = await register_owner()
    token = owner["tokens"]["access_token"]
    tenant_id = UUID(owner["tenant"]["id"])

    cust_res = await client.post(
        "/api/v1/customers/",
        json={"name": "NoMap", "email": "nomap@example.com"},
        headers=auth_headers(token),
    )
    assert cust_res.status_code == 201, cust_res.text
    customer = cust_res.json()

    inv_res = await client.post(
        "/api/v1/invoices/",
        json={
            "customer_id": customer["id"],
            "issue_date": date.today().isoformat(),
            "due_date": date.today().isoformat(),
            "status": "PAID",
            "currency": "USD",
            "items": [{"description": "Service", "quantity": "1", "unit_price": "25.00", "tax_rate": "0"}],
        },
        headers=auth_headers(token),
    )
    assert inv_res.status_code == 201, inv_res.text

    async with async_session_maker() as session:
        lines = await session.execute(select(JournalEntryLine).where(JournalEntryLine.tenant_id == tenant_id))
        assert lines.scalars().first() is None  # no journal entries without mapping
