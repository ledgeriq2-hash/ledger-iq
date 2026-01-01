from __future__ import annotations

import time
from datetime import date

import pytest
from httpx import AsyncClient


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_bulk_invoices_performance(client: AsyncClient, register_owner):
    owner = await register_owner()
    token = owner["tokens"]["access_token"]

    cust = (
        await client.post(
            "/api/v1/customers/",
            json={"code": "PERF-001", "name": "Perf Cust", "email": "perf@example.com"},
            headers=auth_headers(token),
        )
    ).json()

    for _ in range(30):
        payload = {
            "customer_id": cust["id"],
            "issue_date": date.today().isoformat(),
            "due_date": date.today().isoformat(),
            "status": "SENT",
            "currency": "USD",
            "items": [
                {"description": "Perf", "quantity": "1", "unit_price": "5.00", "tax_rate": "0", "line_total": "5.00"}
            ],
        }
        res = await client.post("/api/v1/invoices/", json=payload, headers=auth_headers(token))
        assert res.status_code == 201, res.text

    t0 = time.perf_counter()
    list_res = await client.get("/api/v1/invoices/", headers=auth_headers(token))
    elapsed_list = time.perf_counter() - t0
    assert list_res.status_code == 200, list_res.text
    assert elapsed_list < 2.0, f"Invoice list slow: {elapsed_list:.2f}s"

    t0 = time.perf_counter()
    tb_res = await client.get(
        "/api/v1/reports/trial-balance",
        params={"as_of_date": date.today().isoformat()},
        headers=auth_headers(token),
    )
    elapsed_tb = time.perf_counter() - t0
    assert tb_res.status_code == 200, tb_res.text
    assert elapsed_tb < 2.0, f"Trial balance slow: {elapsed_tb:.2f}s"
