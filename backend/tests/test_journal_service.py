from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.models.journal_entry import JournalEntry
from app.models.journal_entry_line import JournalEntryLine
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

    async def execute(self, *_args, **_kwargs):
        return None


def _sum_debits(lines: list[JournalEntryLine]) -> Decimal:
    return sum((line.debit for line in lines), Decimal("0"))


def _sum_credits(lines: list[JournalEntryLine]) -> Decimal:
    return sum((line.credit for line in lines), Decimal("0"))


@pytest.mark.asyncio
async def test_create_journal_entry_with_lines_balanced():
    session = FakeSession()
    tenant_id = uuid4()
    lines = [
        {"account_id": uuid4(), "debit": Decimal("100"), "credit": Decimal("0"), "line_description": "Cash"},
        {"account_id": uuid4(), "debit": Decimal("0"), "credit": Decimal("100"), "line_description": "Revenue"},
    ]

    entry = await journal_service.create_journal_entry_with_lines(
        session=session,
        tenant_id=tenant_id,
        date=date(2024, 1, 1),
        description="Sale",
        reference="INV-1",
        lines=lines,
    )

    assert isinstance(entry, JournalEntry)
    # The last two added objects are the lines
    added_lines = [obj for obj in session.added if isinstance(obj, JournalEntryLine)]
    assert _sum_debits(added_lines) == _sum_credits(added_lines) == Decimal("100")


@pytest.mark.asyncio
async def test_create_multicurrency_entry():
    session = FakeSession()
    tenant_id = uuid4()
    lines = [
        {"account_id": uuid4(), "debit": Decimal("50"), "credit": Decimal("0"), "currency_amount": Decimal("2000")},
        {"account_id": uuid4(), "debit": Decimal("0"), "credit": Decimal("50"), "currency_amount": Decimal("2000")},
    ]

    entry = await journal_service.create_journal_entry_with_lines(
        session=session,
        tenant_id=tenant_id,
        date=date(2024, 2, 1),
        description="FX Entry",
        reference="FX-1",
        lines=lines,
        currency_code="EUR",
        fx_rate=1.1,
    )

    added_lines = [obj for obj in session.added if isinstance(obj, JournalEntryLine)]
    assert entry.currency_code == "EUR"
    assert entry.fx_rate == 1.1
    assert _sum_debits(added_lines) == _sum_credits(added_lines) == Decimal("50")
    assert all(line.currency_amount == Decimal("2000") for line in added_lines)


@pytest.mark.asyncio
async def test_create_reversing_entry(monkeypatch):
    session = FakeSession()
    tenant_id = uuid4()
    original = JournalEntry(
        date=date(2024, 3, 1),
        description="Original",
        reference="JE-1",
        is_posted=True,
        currency_code="USD",
        fx_rate=1.0,
        source_module="invoice",
        source_id=uuid4(),
        tenant_id=tenant_id,
    )
    original_line = JournalEntryLine(
        account_id=uuid4(),
        debit=Decimal("75"),
        credit=Decimal("0"),
        currency_amount=Decimal("3000"),
        line_description="Original line",
        tenant_id=tenant_id,
        journal_entry_id=original.id,
    )
    original.lines = [original_line]

    async def fake_get_entry(_session, _tenant, _entry_id):
        return original

    monkeypatch.setattr(journal_service, "get_journal_entry", fake_get_entry)

    reversing_entry = await journal_service.create_reversing_entry_impl(
        session=session,
        tenant_id=tenant_id,
        original_journal_entry_id=original.id,
        reversal_date=date(2024, 3, 2),
    )

    added_lines = [obj for obj in session.added if isinstance(obj, JournalEntryLine) and obj.journal_entry_id == reversing_entry.id]
    assert reversing_entry.reversed_of_id == original.id
    assert reversing_entry.date == date(2024, 3, 2)
    assert _sum_debits(added_lines) == _sum_credits(added_lines) == Decimal("75")
    assert added_lines[0].debit == Decimal("0")
    assert added_lines[0].credit == Decimal("75")
    assert "Reversal" in (added_lines[0].line_description or "")
