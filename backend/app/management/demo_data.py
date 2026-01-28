from __future__ import annotations

import asyncio
from datetime import UTC, datetime, date, timedelta
from decimal import Decimal
import os

from sqlalchemy import select

from app.database import async_session_maker
from app.initial_data import seed_tenant
from app.models.customer import Customer
from app.models.debt import Debt
from app.models.employee import Employee
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.portal_token import PortalEntityType, PortalToken
from app.models.product import Product
from app.models.unit import InventoryUnit
from app.models.supplier import Supplier
from app.models.treasury import Treasury
from app.models.treasury_transaction import TreasuryTransaction
from app.services import (
    customer_service,
    debt_service,
    invoice_service,
    payment_service,
    product_service,
    portal_service,
    role_service,
    supplier_service,
    tenant_service,
    user_service,
)


async def _get_or_create_tenant(session, name: str, slug: str):
    from app.services import tenant_service as tenant_svc

    existing = await tenant_svc.resolve_tenant(session, slug)
    if existing:
        return existing
    return await tenant_svc.create_tenant(session, {"name": name, "slug": slug}, scope_id=None)


async def _get_or_create_role(session, tenant_id, name: str, permissions: dict | None = None):
    roles = await role_service.list_roles(session, tenant_id)
    for r in roles:
        if r.name.lower() == name.lower():
            return r
    return await role_service.create_role(session, tenant_id, {"name": name, "permissions_json": permissions or {}})


async def _get_or_create_user(session, tenant_id, email: str, password: str, role_id, full_name: str):
    existing = await user_service.get_user_by_email(session, tenant_id, email)
    if existing:
        return existing
    payload = {
        "email": email,
        "password": password,
        "role_id": role_id,
        "full_name": full_name,
        "is_superuser": True,
    }
    return await user_service.create_user(session, tenant_id, payload)


def _get_demo_owner_password() -> str:
    password = os.environ.get("DEMO_OWNER_PASSWORD")
    if not password:
        raise RuntimeError("DEMO_OWNER_PASSWORD environment variable is required to create demo data")
    return password


async def _ensure_customers(session, tenant):
    customers_payload = [
        {"code": "ACME", "name": "Acme Corp", "email": "ar@acme.com", "phone": "555-1000"},
        {"code": "GLOBEX", "name": "Globex LLC", "email": "billing@globex.com", "phone": "555-2000"},
        {"code": "INITECH", "name": "Initech", "email": "ap@initech.com", "phone": "555-3000"},
        {"code": "UMBRELLA", "name": "Umbrella Co", "email": "finance@umbrella.com", "phone": "555-4000"},
    ]
    created = []
    for payload in customers_payload:
        existing = await session.execute(
            select(Customer).where(Customer.tenant_id == tenant.id, Customer.email == payload["email"])
        )
        customer = existing.scalar_one_or_none()
        if not customer:
            customer = await customer_service.create_customer(session, tenant.id, payload)
        created.append(customer)
    return created


async def _ensure_suppliers(session, tenant):
    suppliers_payload = [
        {"code": "NORTHWIND", "name": "Northwind Traders", "email": "northwind@example.com"},
        {"code": "ACME-SUP", "name": "Acme Supplies", "email": "supplies@acme.com"},
    ]
    created = []
    for payload in suppliers_payload:
        existing = await session.execute(
            select(Supplier).where(Supplier.tenant_id == tenant.id, Supplier.email == payload["email"])
        )
        supplier = existing.scalar_one_or_none()
        if not supplier:
            supplier = await supplier_service.create_supplier(session, tenant.id, payload)
        created.append(supplier)
    return created


async def _ensure_employees(session, tenant):
    employees_payload = [
        {"code": "EMP-ALICE", "name": "Alice Accounts", "email": "alice@demo.local"},
        {"code": "EMP-BOB", "name": "Bob Ops", "email": "bob@demo.local"},
    ]
    created = []
    for payload in employees_payload:
        existing = await session.execute(
            select(Employee).where(Employee.tenant_id == tenant.id, Employee.email == payload["email"])
        )
        employee = existing.scalar_one_or_none()
        if not employee:
            employee = Employee(**payload, tenant_id=tenant.id)
            session.add(employee)
            await session.flush()
        created.append(employee)
    return created


async def _ensure_base_unit(session, tenant):
    existing = await session.execute(
        select(InventoryUnit)
        .where(InventoryUnit.tenant_id == tenant.id)
        .order_by(InventoryUnit.created_at.asc())
    )
    unit = existing.scalars().first()
    if unit:
        return unit
    unit = InventoryUnit(
        tenant_id=tenant.id,
        code="EA",
        name="Each",
        ratio_to_base=Decimal("1"),
        is_base=True,
    )
    session.add(unit)
    await session.commit()
    await session.refresh(unit)
    return unit


async def _ensure_products(session, tenant):
    base_unit = await _ensure_base_unit(session, tenant)
    products_payload = [
        {
            "name": "Consulting Hours",
            "sku": "CONS-01",
            "unit_price": Decimal("150.00"),
            "is_service": True,
            "base_unit_id": base_unit.id,
        },
        {
            "name": "Implementation Package",
            "sku": "IMPL-10",
            "unit_price": Decimal("1200.00"),
            "is_service": True,
            "base_unit_id": base_unit.id,
        },
        {
            "name": "Support Plan",
            "sku": "SUP-99",
            "unit_price": Decimal("299.00"),
            "is_service": True,
            "base_unit_id": base_unit.id,
        },
    ]
    created = []
    for payload in products_payload:
        existing = await session.execute(
            select(Product)
            .where(Product.tenant_id == tenant.id)
            .where(Product.sku == payload["sku"])
        )
        product = existing.scalar_one_or_none()
        if not product:
            product = await product_service.create_product(session, tenant.id, payload)
        created.append(product)
    return created


async def _ensure_invoices(session, tenant, customers, products):
    today = date.today()
    invoices_payloads = [
        {
            "customer_id": customers[0].id,
            "issue_date": today.isoformat(),
            "due_date": (today + timedelta(days=15)).isoformat(),
            "status": "PAID",
            "currency": "USD",
            "items": [
                {
                    "product_id": products[0].id,
                    "description": "Consulting retainer",
                    "quantity": "10",
                    "unit_price": str(products[0].unit_price),
                    "tax_rate": "0",
                }
            ],
        },
        {
            "customer_id": customers[1].id,
            "issue_date": today.isoformat(),
            "due_date": (today + timedelta(days=30)).isoformat(),
            "status": "SENT",
            "currency": "USD",
            "items": [
                {
                    "product_id": products[1].id,
                    "description": "Implementation milestone 1",
                    "quantity": "1",
                    "unit_price": str(products[1].unit_price),
                    "tax_rate": "0",
                }
            ],
        },
        {
            "customer_id": customers[2].id,
            "issue_date": (today - timedelta(days=10)).isoformat(),
            "due_date": (today + timedelta(days=5)).isoformat(),
            "status": "SENT",
            "currency": "USD",
            "items": [
                {
                    "product_id": products[2].id,
                    "description": "Support plan quarterly",
                    "quantity": "1",
                    "unit_price": str(products[2].unit_price),
                    "tax_rate": "0",
                }
            ],
        },
    ]
    created = []
    for payload in invoices_payloads:
        existing = await session.execute(
            select(Invoice)
            .where(Invoice.tenant_id == tenant.id)
            .where(Invoice.customer_id == payload["customer_id"])
            .where(Invoice.status == payload["status"])
        )
        invoice = existing.scalar_one_or_none()
        if not invoice:
            invoice = await invoice_service.create_invoice(session, tenant.id, payload)
        created.append(invoice)
    return created


async def _ensure_payments(session, tenant, invoices):
    payments_payloads = [
        {
            "invoice_id": invoices[0].id,
            "customer_id": invoices[0].customer_id,
            "amount": invoices[0].total_amount,
            "method": "bank_transfer",
        },
        {
            "invoice_id": invoices[1].id,
            "customer_id": invoices[1].customer_id,
            "amount": Decimal("500.00"),
            "method": "card",
            "reference": "PARTIAL-1",
        },
    ]
    for payload in payments_payloads:
        existing = await session.execute(
            select(Payment)
            .where(Payment.tenant_id == tenant.id)
            .where(Payment.invoice_id == payload["invoice_id"])
            .where(Payment.amount == payload["amount"])
        )
        if not existing.scalar_one_or_none():
            await payment_service.create_payment(session, tenant.id, payload)


async def _ensure_debts(session, tenant, suppliers):
    for supplier in suppliers:
        existing = await session.execute(
            select(Debt)
            .where(Debt.tenant_id == tenant.id)
            .where(Debt.supplier_id == supplier.id)
        )
        if not existing.scalar_one_or_none():
            await debt_service.create_debt(
                session,
                tenant.id,
                {
                    "supplier_id": supplier.id,
                    "description": f"Opening balance for {supplier.name}",
                    "amount": Decimal("1500.00"),
                    "currency": "USD",
                    "status": "open",
                },
            )


async def _ensure_treasury_transactions(session, tenant):
    treasury = await session.execute(select(Treasury).where(Treasury.tenant_id == tenant.id))
    treasury_obj = treasury.scalar_one_or_none()
    if not treasury_obj:
        return
    existing = await session.execute(
        select(TreasuryTransaction)
        .where(TreasuryTransaction.tenant_id == tenant.id)
        .where(TreasuryTransaction.treasury_id == treasury_obj.id)
    )
    if existing.scalar_one_or_none():
        return
    for direction, amount in [("in", Decimal("5000")), ("out", Decimal("1200"))]:
        tx = TreasuryTransaction(
            treasury_id=treasury_obj.id,
            amount=amount,
            direction=direction,
            reference_type="demo",
            description="Demo flow",
            tenant_id=tenant.id,
        )
        session.add(tx)


async def _ensure_portal_token(session, tenant, customer):
    existing = await session.execute(
        select(PortalToken)
        .where(PortalToken.tenant_id == tenant.id)
        .where(PortalToken.entity_type == PortalEntityType.CUSTOMER)
        .where(PortalToken.entity_id == customer.id)
    )
    if existing.scalar_one_or_none():
        return
    expires_at = datetime.now(UTC) + timedelta(days=7)
    await portal_service.create_portal_token_for_customer(session, tenant.id, customer.id, expires_at)


async def create_demo_data() -> None:
    async with async_session_maker() as session:
        tenant = await _get_or_create_tenant(session, "Demo Tenant", "demo-ledger")
        await seed_tenant(session, tenant)

        owner_role = await _get_or_create_role(session, tenant.id, "OWNER", {"all": True})
        owner_user = await _get_or_create_user(
            session,
            tenant.id,
            email="demo.owner@example.com",
            password=_get_demo_owner_password(),
            role_id=owner_role.id,
            full_name="Demo Owner",
        )

        customers = await _ensure_customers(session, tenant)
        suppliers = await _ensure_suppliers(session, tenant)
        await _ensure_employees(session, tenant)
        products = await _ensure_products(session, tenant)
        invoices = await _ensure_invoices(session, tenant, customers, products)
        await _ensure_payments(session, tenant, invoices)
        await _ensure_debts(session, tenant, suppliers)
        await _ensure_treasury_transactions(session, tenant)
        await _ensure_portal_token(session, tenant, customers[0])

        await session.commit()

    print("Demo tenant created:")
    print(f"- Tenant slug: {tenant.slug}")
    print(f"- Owner email: {owner_user.email}")
    print("- Owner password: [provided via DEMO_OWNER_PASSWORD]")


def main():
    asyncio.run(create_demo_data())


if __name__ == "__main__":
    main()
