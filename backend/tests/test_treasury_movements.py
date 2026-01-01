from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import AppException
from app.database import async_session_maker
from app.services import supplier_service


@pytest.mark.anyio
async def test_inactive_and_deleted_supplier_block_movements(register_owner):
    auth = await register_owner()
    tenant_id = uuid.UUID(auth["tenant"]["id"])

    async with async_session_maker() as session:
        supplier = await supplier_service.create_supplier(
            session,
            tenant_id,
            {
                "code": "BLOCK-001",
                "name": "Blocked Supplier",
                "email": "blocked@example.com",
            },
        )
        await supplier_service.deactivate_supplier(session, tenant_id, supplier.id)
        with pytest.raises(AppException) as exc:
            await supplier_service.validate_can_receive_movements(session, tenant_id, supplier.id)
        assert exc.value.http_status == 409
        assert exc.value.code == "supplier_inactive"

        await supplier_service.soft_delete_supplier(session, tenant_id, supplier.id)
        with pytest.raises(AppException) as exc_deleted:
            await supplier_service.validate_can_receive_movements(session, tenant_id, supplier.id)
        assert exc_deleted.value.http_status == 409
        assert exc_deleted.value.code == "supplier_deleted"
