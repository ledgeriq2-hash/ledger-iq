from __future__ import annotations

from sqlalchemy import Column, Table
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


def register_treasury_shims() -> None:
    """TEST-ONLY SHIM; DO NOT USE IN PROD."""
    if "treasury_transactions" in Base.metadata.tables:
        return
    Table(
        "treasury_transactions",
        Base.metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
    )


__all__ = ["register_treasury_shims"]
