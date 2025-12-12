from __future__ import annotations

import asyncio
from datetime import date, timedelta
from decimal import Decimal

from app.database import async_session_maker
from app.initial_data import seed_tenant
from app.services import (
    customer_service,
    invoice_service,
    payment_service,
    product_service,
    role_service,
    tenant_service,
    user_service,
)


async def _get_or_create_tenant(session, name: str, slug: str):
    existing = await tenant_service.resolve_tenant(session, slug)
    if existing:
        return existing
    return await tenant_service.create_tenant(session, {"name": name, "slug": slug}, scope_id=None)


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


async def create_demo_data() -> None:
    async with async_session_maker() as session:
        tenant = await _get_or_create_tenant(session, "Demo Tenant", "demo-ledger")
        await seed_tenant(session, tenant)

        owner_role = await _get_or_create_role(session, tenant.id, "OWNER", {"all": True})
        owner_user = await _get_or_create_user(
            session,
            tenant.id,
            email="demo.owner@example.com",
            password="DemoPass123!",
            role_id=owner_role.id,
            full_name="Demo Owner",
        )

        # Customers
        customers_data = [
            {"name": "Acme Corp", "email": "ar@acme.com", "phone": "555-1000"},
            {"name": "Globex LLC", "email": "billing@globex.com", "phone": "555-2000"},
            {"name": "Initech", "email": "ap@initech.com", "phone": "555-3000"},
            {"name": "Umbrella Co", "email": "finance@umbrella.com", "phone": "555-4000"},
        ]
        customers = []
        for data in customers_data:
            customers.append(await customer_service.create_customer(session, tenant.id, data))

        # Products
        products_data = [
            {"name": "Consulting Hours", "sku": "CONS-01", "unit_price": Decimal("150.00"), "is_service": True},
            {"name": "Implementation Package", "sku": "IMPL-10", "unit_price": Decimal("1200.00"), "is_service": True},
            {"name": "Support Plan", "sku": "SUP-99", "unit_price": Decimal("299.00"), "is_service": True},
        ]
        products = []
        for data in products_data:
            products.append(await product_service.create_product(session, tenant.id, data))

        # Invoices
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
                        "line_total": str(Decimal("10") * products[0].unit_price),
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
                        "line_total": str(products[1].unit_price),
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
                        "line_total": str(products[2].unit_price),
                    }
                ],
            },
        ]

        invoices = []
        for payload in invoices_payloads:
            invoices.append(await invoice_service.create_invoice(session, tenant.id, payload))

        # Payments (full for first, partial for second)
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
            await payment_service.create_payment(session, tenant.id, payload)

        print("Demo tenant created:")
        print(f"- Tenant slug: {tenant.slug}")
        print(f"- Owner email: {owner_user.email}")
        print(f"- Owner password: DemoPass123!")


def main():
    asyncio.run(create_demo_data())


if __name__ == "__main__":
    main()
