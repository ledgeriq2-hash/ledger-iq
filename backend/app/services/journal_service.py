from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Iterable, Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journal_entry import JournalEntry
from app.models.journal_entry_line import JournalEntryLine


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


def validate_journal_balanced(lines: Iterable[dict[str, Any]]) -> bool:
    debit_total = Decimal("0")
    credit_total = Decimal("0")
    for line in lines:
        debit_total += Decimal(str(line.get("debit") or 0))
        credit_total += Decimal(str(line.get("credit") or 0))
    return debit_total.quantize(Decimal("0.01")) == credit_total.quantize(Decimal("0.01"))


def _normalize_line(line: dict[str, Any], tenant_id: UUID, entry_id: UUID) -> JournalEntryLine:
    return JournalEntryLine(
        account_id=line["account_id"],
        debit=Decimal(str(line.get("debit") or 0)),
        credit=Decimal(str(line.get("credit") or 0)),
        currency_amount=(
            Decimal(str(line["currency_amount"])) if line.get("currency_amount") is not None else None
        ),
        line_description=line.get("line_description"),
        tenant_id=tenant_id,
        journal_entry_id=entry_id,
    )


async def list_journal_entries(session: AsyncSession, tenant_id: UUID) -> Sequence[JournalEntry]:
    result = await session.execute(select(JournalEntry).where(JournalEntry.tenant_id == tenant_id))
    return result.scalars().all()


async def get_journal_entry(
    session: AsyncSession, tenant_id: UUID, entry_id: UUID
) -> JournalEntry | None:
    result = await session.execute(
        select(JournalEntry).where(JournalEntry.id == entry_id, JournalEntry.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def _replace_lines(
    session: AsyncSession, entry: JournalEntry, lines_data: list[dict[str, Any]]
) -> list[JournalEntryLine]:
    if not validate_journal_balanced(lines_data):
        raise ValueError("Journal entry is not balanced (debits != credits)")

    await session.execute(
        delete(JournalEntryLine).where(
            JournalEntryLine.journal_entry_id == entry.id, JournalEntryLine.tenant_id == entry.tenant_id
        )
    )
    created_lines: list[JournalEntryLine] = []
    for line_data in lines_data:
        line = _normalize_line(line_data, tenant_id=entry.tenant_id, entry_id=entry.id)
        session.add(line)
        created_lines.append(line)
    return created_lines


async def create_journal_entry(session: AsyncSession, tenant_id: UUID, payload: Any) -> JournalEntry:
    data = _to_dict(payload)
    lines_data = data.pop("lines", None)
    if not lines_data:
        raise ValueError("Journal entry requires at least one line")

    entry = JournalEntry(**data, tenant_id=tenant_id)
    session.add(entry)
    await session.flush()
    created_lines = await _replace_lines(session, entry, lines_data)
    await session.commit()
    await session.refresh(entry)
    return entry


async def update_journal_entry(
    session: AsyncSession, tenant_id: UUID, entry_id: UUID, payload: Any
) -> JournalEntry | None:
    entry = await get_journal_entry(session, tenant_id, entry_id)
    if not entry:
        return None
    data = _to_dict(payload, exclude_unset=True)
    lines_data = data.pop("lines", None)
    for field, value in data.items():
        if field in {"id", "tenant_id", "lines"}:
            continue
        setattr(entry, field, value)
    if lines_data is not None:
        created_lines = await _replace_lines(session, entry, lines_data)
    await session.commit()
    await session.refresh(entry)
    return entry


async def create_journal_entry_with_lines(
    session: AsyncSession,
    tenant_id: UUID,
    date: date,
    description: str | None,
    lines: list[dict[str, Any]],
    reference: str | None = None,
    *,
    currency_code: str | None = None,
    fx_rate: float | Decimal | None = None,
    source_module: str | None = None,
    source_id: UUID | None = None,
    is_posted: bool = True,
    reversed_of_id: UUID | None = None,
) -> JournalEntry:
    """
    Convenience helper to create a journal entry and its lines atomically.

    Supports multi-currency fields and source metadata.
    """
    if not lines:
        raise ValueError("Journal entry requires at least one line")
    if not validate_journal_balanced(lines):
        raise ValueError("Journal entry is not balanced (debits != credits)")

    entry = JournalEntry(
        date=date,
        description=description,
        reference=reference,
        is_posted=is_posted,
        currency_code=currency_code,
        fx_rate=float(fx_rate) if fx_rate is not None else None,
        source_module=source_module,
        source_id=source_id,
        reversed_of_id=reversed_of_id,
        tenant_id=tenant_id,
    )
    session.add(entry)
    await session.flush()

    created_lines: list[JournalEntryLine] = []
    for line in lines:
        created_line = _normalize_line(line, tenant_id=tenant_id, entry_id=entry.id)
        session.add(created_line)
        created_lines.append(created_line)

    await session.commit()
    await session.refresh(entry)
    return entry


async def create_reversing_entry(*args, **kwargs):
    """Backward-compatibility shim; prefer the fully typed create_reversing_entry_impl."""
    return await create_reversing_entry_impl(*args, **kwargs)


async def create_reversing_entry_impl(
    session: AsyncSession,
    tenant_id: UUID,
    original_journal_entry_id: UUID,
    reversal_date: date,
) -> JournalEntry:
    """
    Create a reversing journal entry for the given original entry.

    - Copies currency, fx_rate, source_module, source_id.
    - Sets reversed_of_id to the original entry.
    - Swaps debit/credit on each line.
    """
    original = await get_journal_entry(session, tenant_id, original_journal_entry_id)
    if not original:
        raise ValueError("Original journal entry not found")

    reversed_lines: list[dict[str, Any]] = []
    for line in original.lines:
        reversed_lines.append(
            {
                "account_id": line.account_id,
                "debit": line.credit,
                "credit": line.debit,
                "currency_amount": line.currency_amount,
                "line_description": f"Reversal of {line.line_description}" if line.line_description else "Reversal",
            }
        )

    new_entry = JournalEntry(
        date=reversal_date,
        description=original.description or f"Reversal of {original.reference or original.id}",
        reference=original.reference,
        is_posted=True,
        currency_code=original.currency_code,
        fx_rate=original.fx_rate,
        source_module=original.source_module,
        source_id=original.source_id,
        reversed_of_id=original.id,
        tenant_id=tenant_id,
    )
    session.add(new_entry)
    await session.flush()

    for line in reversed_lines:
        session.add(_normalize_line(line, tenant_id=tenant_id, entry_id=new_entry.id))

    await session.commit()
    await session.refresh(new_entry)
    return new_entry


async def delete_journal_entry(session: AsyncSession, tenant_id: UUID, entry_id: UUID) -> bool:
    await session.execute(
        delete(JournalEntryLine).where(
            JournalEntryLine.journal_entry_id == entry_id, JournalEntryLine.tenant_id == tenant_id
        )
    )
    result = await session.execute(
        delete(JournalEntry).where(JournalEntry.id == entry_id, JournalEntry.tenant_id == tenant_id)
    )
    await session.commit()
    return result.rowcount > 0


__all__ = [
    "list_journal_entries",
    "get_journal_entry",
    "create_journal_entry",
    "create_journal_entry_with_lines",
    "update_journal_entry",
    "delete_journal_entry",
    "validate_journal_balanced",
    "create_reversing_entry",
    "create_reversing_entry_impl",
]
