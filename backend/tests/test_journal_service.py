from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.exceptions import AppException
from app.services import journal_service


class FakeSession:
    def __init__(self):
        self.added: list[object] = []
        self.commits = 0

    async def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        self.commits += 1
        return None

    async def refresh(self, _obj):
        return None

    async def execute(self, *_args, **_kwargs):  # pragma: no cover
        return None


@pytest.mark.asyncio
async def test_create_journal_entry_with_lines_disabled():
    session = FakeSession()
    tenant_id = uuid4()
    lines = [
        {"account_id": uuid4(), "debit": Decimal("100"), "credit": Decimal("0"), "line_description": "Cash"},
        {"account_id": uuid4(), "debit": Decimal("0"), "credit": Decimal("100"), "line_description": "Revenue"},
    ]

    with pytest.raises(AppException) as exc:
        await journal_service.create_journal_entry_with_lines(
            session=session,
            tenant_id=tenant_id,
            date=date(2024, 1, 1),
            description="Sale",
            reference="INV-1",
            lines=lines,
        )
    assert exc.value.http_status == 405


@pytest.mark.asyncio
async def test_create_multicurrency_entry_disabled():
    session = FakeSession()
    tenant_id = uuid4()
    lines = [
        {"account_id": uuid4(), "debit": Decimal("50"), "credit": Decimal("0"), "currency_amount": Decimal("2000")},
        {"account_id": uuid4(), "debit": Decimal("0"), "credit": Decimal("50"), "currency_amount": Decimal("2000")},
    ]

    with pytest.raises(AppException) as exc:
        await journal_service.create_journal_entry_with_lines(
            session=session,
            tenant_id=tenant_id,
            date=date(2024, 2, 1),
            description="FX Entry",
            reference="FX-1",
            lines=lines,
            currency_code="EUR",
            fx_rate=1.1,
        )
    assert exc.value.http_status == 405


@pytest.mark.asyncio
async def test_create_reversing_entry_disabled(monkeypatch):
    session = FakeSession()
    tenant_id = uuid4()

    async def fake_get_entry(_session, _tenant, _entry_id):
        return None

    monkeypatch.setattr(journal_service, "get_journal_entry", fake_get_entry)

    with pytest.raises(AppException) as exc:
        await journal_service.create_reversing_entry_impl(
            session=session,
            tenant_id=tenant_id,
            original_journal_entry_id=uuid4(),
            reversal_date=date(2024, 3, 2),
        )
    assert exc.value.http_status == 405
