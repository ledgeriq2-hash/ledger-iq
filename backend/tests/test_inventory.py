from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session_maker
from app.models.product import Product
from app.initial_data import seed_tenant
from app.models.stock_movement import ReferenceType, StockMovement
from app.models.tenant import Tenant


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _ensure_seeded(tenant_id: str) -> None:
    tenant_uuid = UUID(tenant_id)
    async with async_session_maker() as session:
        tenant = await session.get(Tenant, tenant_uuid)
        await seed_tenant(session, tenant)


@pytest.mark.anyio
async def test_movement_creation_and_negative_block(client: AsyncClient, register_owner):
    owner = await register_owner()
    headers = auth_headers(owner["tokens"]["access_token"])

    prod_res = await client.post(
        "/api/v1/products/",
        json={"name": "Widget", "sku": "W-1", "unit_price": "10.00", "cost_price": "5.00", "stock_quantity": "5"},
        headers=headers,
    )
    assert prod_res.status_code == 201, prod_res.text
    product = prod_res.json()

    # Valid OUT within stock
    out_res = await client.post(
        "/api/v1/inventory/movements",
        json={
          "product_id": product["id"],
          "quantity": "2",
          "movement_type": "OUT",
          "reference_type": "MANUAL"
        },
        headers=headers,
    )
    assert out_res.status_code == 201, out_res.text

    # Exceeding stock should fail
    too_far = await client.post(
        "/api/v1/inventory/movements",
        json={
          "product_id": product["id"],
          "quantity": "10",
          "movement_type": "OUT",
          "reference_type": "MANUAL"
        },
        headers=headers,
    )
    assert too_far.status_code == 400
    body = too_far.json()
    assert body["code"] == "stock_negative"

    # Summary reflects remaining stock 3
    summary = await client.get("/api/v1/inventory/summary", headers=headers)
    assert summary.status_code == 200
    items = summary.json()["items"]
    widget = next(i for i in items if i["product_id"] == product["id"])
    assert Decimal(widget["stock_quantity"]) == Decimal("3.00")


@pytest.mark.anyio
async def test_invoice_creates_out_movements(client: AsyncClient, register_owner):
    owner = await register_owner()
    headers = auth_headers(owner["tokens"]["access_token"])
    await _ensure_seeded(owner["tenant"]["id"])

    cust_res = await client.post(
        "/api/v1/customers/",
        json={"code": "BUYER-001", "name": "Buyer", "email": "buyer@example.com"},
        headers=headers,
    )
    assert cust_res.status_code == 201, cust_res.text
    customer = cust_res.json()

    prod_res = await client.post(
        "/api/v1/products/",
        json={"name": "Stocked", "sku": "ST-1", "unit_price": "10.00", "cost_price": "4.00", "stock_quantity": "10"},
        headers=headers,
    )
    product = prod_res.json()

    inv_res = await client.post(
        "/api/v1/invoices/",
        json={
            "customer_id": customer["id"],
            "issue_date": "2025-01-01",
            "currency": "USD",
            "status": "SENT",
            "items": [
                {"product_id": product["id"], "description": "Item", "quantity": "4", "unit_price": "10.00", "tax_rate": "0"}
            ],
        },
        headers=headers,
    )
    assert inv_res.status_code == 201, inv_res.text

    post_res = await client.post(f"/api/v1/invoices/{inv_res.json()['id']}/post", headers=headers)
    assert post_res.status_code == 200, post_res.text

    async with async_session_maker() as session:
        stock_row = await session.execute(select(Product).where(Product.id == UUID(product["id"])))
        product_db = stock_row.scalar_one()
        assert Decimal(product_db.stock_quantity) == Decimal("6.00")

        mov = await session.execute(select(StockMovement).where(StockMovement.reference_type == ReferenceType.INVOICE))
        assert mov.scalars().first() is not None


@pytest.mark.anyio
async def test_inventory_multi_tenant_isolation(client: AsyncClient, register_owner):
    owner1 = await register_owner()
    owner2 = await register_owner()

    prod1 = await client.post(
        "/api/v1/products/",
        json={"name": "A", "sku": "A1", "unit_price": "1", "cost_price": "1", "stock_quantity": "1"},
        headers=auth_headers(owner1["tokens"]["access_token"]),
    )
    assert prod1.status_code == 201

    move_other = await client.get("/api/v1/inventory/movements", headers=auth_headers(owner2["tokens"]["access_token"]))
    assert move_other.status_code == 200
    assert move_other.json()["items"] == []
