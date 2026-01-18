"""Backfill role permissions for Sprint 4.

Revision ID: 0004_sprint4_permission_backfill
Revises: 0003_sprint3_journal_constraints
Create Date: 2026-01-18 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from app.core.permissions import ROLE_PERMISSION_PRESETS

revision = "0004_sprint4_permission_backfill"
down_revision = "0003_sprint3_journal_constraints"
branch_labels = None
depends_on = None


def _normalize_codes(raw_codes: object) -> set[str]:
    if raw_codes is None:
        return set()
    if isinstance(raw_codes, str):
        return {raw_codes}
    if isinstance(raw_codes, (list, tuple, set, frozenset)):
        return {str(code) for code in raw_codes if code is not None}
    return set()


def _merge_permissions(existing: object, preset: dict) -> dict:
    if isinstance(existing, dict):
        merged = dict(existing)
    else:
        merged = {}

    for key, value in preset.items():
        if key == "codes":
            existing_codes = _normalize_codes(merged.get("codes"))
            preset_codes = _normalize_codes(value)
            merged_codes = sorted(existing_codes.union(preset_codes))
            if merged_codes:
                merged["codes"] = merged_codes
            continue
        if isinstance(value, bool):
            if value:
                merged[key] = True
            continue
        if key not in merged:
            merged[key] = value
    return merged


def upgrade() -> None:
    bind = op.get_bind()
    roles = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("permissions_json", JSONB),
    )

    presets_by_name = {name.upper(): preset for name, preset in ROLE_PERMISSION_PRESETS.items()}
    target_names = tuple(presets_by_name.keys())

    result = bind.execute(
        sa.select(roles.c.id, roles.c.name, roles.c.permissions_json).where(
            sa.func.upper(roles.c.name).in_(target_names)
        )
    )
    rows = result.fetchall()

    for row in rows:
        role_name = str(row.name or "").upper()
        preset = presets_by_name.get(role_name)
        if not preset:
            continue
        merged = _merge_permissions(row.permissions_json, preset)
        current = row.permissions_json if isinstance(row.permissions_json, dict) else {}
        if merged != current:
            bind.execute(
                sa.update(roles)
                .where(roles.c.id == row.id)
                .values(permissions_json=merged)
            )


def downgrade() -> None:
    pass
