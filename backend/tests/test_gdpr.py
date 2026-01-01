from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from app.config import get_settings
from app.core.security import get_password_hash
from app.database import async_session_maker
from app.models.customer import Customer
from app.models.employee import Employee
from app.models.feedback import Feedback
from app.models.gdpr_request import GdprRequest
from app.models.supplier import Supplier
from app.models.tenant import Tenant
from app.models.user import User
from app.tasks import gdpr_tasks


@pytest.mark.anyio
async def test_gdpr_export_creates_artifact(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(tmp_path))
    async with async_session_maker() as session:
        tenant = Tenant(name="ExportCo", slug=f"exp-{uuid4().hex[:6]}")
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        req = GdprRequest(tenant_id=tenant.id, action="export", status="pending")
        session.add(req)
        await session.commit()
        await session.refresh(req)

        gdpr_tasks.run_export(str(req.id))
        await session.refresh(req)
        assert req.status == "ready"
        assert req.artifact_path is not None
    assert Path(req.artifact_path).exists()


@pytest.mark.anyio
async def test_gdpr_export_uses_request_id(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(tmp_path))
    async with async_session_maker() as session:
        tenant = Tenant(name="ExportCo", slug=f"exp-{uuid4().hex[:6]}")
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        req = GdprRequest(tenant_id=tenant.id, action="export", status="pending")
        session.add(req)
        await session.commit()
        await session.refresh(req)

        gdpr_tasks.run_export(str(req.id))
        await session.refresh(req)

        artifact_path = Path(req.artifact_path)
        assert artifact_path.name == f"{tenant.id}_{req.id}.json"
        assert artifact_path.parent.name == "gdpr_exports"
        assert Path(req.artifact_path).exists()


@pytest.mark.anyio
async def test_gdpr_delete_removes_tenant_data(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(tmp_path))
    settings = get_settings()
    settings.gdpr_financial_retention_days = 0
    async with async_session_maker() as session:
        tenant = Tenant(name="DeleteCo", slug=f"del-{uuid4().hex[:6]}")
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        feedback = Feedback(tenant_id=tenant.id, category="bug", message="remove me")
        session.add(feedback)
        req = GdprRequest(tenant_id=tenant.id, action="delete", status="pending")
        session.add(req)
        await session.commit()
        await session.refresh(req)

        gdpr_tasks.run_delete(str(req.id))
        await session.refresh(req)
        assert req.status == "deleted"
        remaining = await session.execute(
            Feedback.__table__.select().where(Feedback.tenant_id == tenant.id)
        )
    assert remaining.fetchall() == []


@pytest.mark.anyio
async def test_gdpr_delete_with_retention_anonymizes(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(tmp_path))
    settings = get_settings()
    settings.gdpr_financial_retention_days = 30

    async with async_session_maker() as session:
        tenant = Tenant(name="RetentionCo", slug=f"ret-{uuid4().hex[:6]}")
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        customer = Customer(
            code="GDPR-CUST",
            name="PII Customer",
            email="client@example.com",
            phone="555-1234",
            tax_id="CUST-TAX",
            tenant_id=tenant.id,
        )
        supplier = Supplier(
            name="PII Supplier",
            email="supplier@example.com",
            phone="555-5678",
            address="321 Road",
            tax_id="SUP-TAX",
            tenant_id=tenant.id,
        )
        employee = Employee(
            name="PII Employee",
            email="employee@example.com",
            phone="555-9012",
            address="789 Blvd",
            tax_id="EMP-TAX",
            tenant_id=tenant.id,
        )
        feedback = Feedback(tenant_id=tenant.id, category="issue", message="sensitive")
        user = User(
            tenant_id=tenant.id,
            email="user@example.com",
            full_name="Sensitive User",
            hashed_password=get_password_hash("Secret1!"),
        )
        session.add_all([customer, supplier, employee, feedback, user])
        await session.commit()
        await session.refresh(customer)
        await session.refresh(supplier)
        await session.refresh(employee)
        await session.refresh(feedback)
        await session.refresh(user)

        req = GdprRequest(tenant_id=tenant.id, action="delete", status="pending")
        session.add(req)
        await session.commit()
        await session.refresh(req)

        gdpr_tasks.run_delete(str(req.id))
        await session.refresh(req)

        assert req.status == "retention_pending"

        async with async_session_maker() as verify_session:
            refreshed_customer = await verify_session.get(Customer, customer.id)
            assert refreshed_customer is not None
            assert refreshed_customer.name == "[GDPR_ANONYMIZED]"
            assert refreshed_customer.email is None
            assert refreshed_customer.phone is None
            assert refreshed_customer.tax_id is None

            refreshed_supplier = await verify_session.get(Supplier, supplier.id)
            assert refreshed_supplier.phone is None
            assert refreshed_supplier.address is None
            assert refreshed_supplier.tax_id is None
            assert refreshed_supplier.name == "[GDPR_ANONYMIZED]"

            refreshed_employee = await verify_session.get(Employee, employee.id)
            assert refreshed_employee.name == "[GDPR_ANONYMIZED]"
            assert refreshed_employee.email is None
            assert refreshed_employee.phone is None
            assert refreshed_employee.address is None
            assert refreshed_employee.tax_id is None

            refreshed_feedback = await verify_session.get(Feedback, feedback.id)
            assert refreshed_feedback.message == "[GDPR_ANONYMIZED]"
            assert refreshed_feedback.category == "[GDPR_ANONYMIZED]"

            refreshed_user = await verify_session.get(User, user.id)
            assert refreshed_user.full_name == "[GDPR_ANONYMIZED]"
            assert refreshed_user.email.startswith("gdpr-deleted-")
            assert refreshed_user.is_active is False
