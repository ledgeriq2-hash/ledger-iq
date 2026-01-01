from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.dto import RecordFinancialTransactionInput, TreasuryMovementInput
from app.accounting.use_cases.record_financial_transaction import record_financial_transaction
from app.core.exceptions import AppException
from app.models.customer import Customer, CustomerStatus
from app.services import employee_service, supplier_service
from app.models.treasury_transaction import TreasuryTransaction
from app.services import audit_log_service
from app.services.accounting_mapping import ACCOUNT_MAPPING_REQUIREMENTS, validate_tenant_account_mapping

MovementType = Literal[
    "receipt",
    "disbursement",
    "expense",
    "payroll_payout",
    "supplier_payment",
    "employee_payment",
]


def _quantize(amount: Decimal | str | int | float) -> Decimal:
    return Decimal(str(amount)).quantize(Decimal("0.01"))


def _select_cash_account(mapping: dict[str, Any]) -> UUID | None:
    if mapping.get("cash_account_id"):
        return mapping["cash_account_id"]
    cashflow = mapping.get("cashflow_account_ids") or []
    if cashflow:
        return cashflow[0]
    if mapping.get("bank_account_id"):
        return mapping["bank_account_id"]
    return None


async def _assert_party_active(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    party_type: str | None,
    party_id: UUID | None,
) -> None:
    if not party_type or not party_id:
        return
    normalized = party_type.strip().lower()
    if normalized in {"client", "customer"}:
        result = await session.execute(
            select(Customer).where(Customer.id == party_id, Customer.tenant_id == tenant_id)
        )
        customer = result.scalar_one_or_none()
        if not customer:
            raise AppException(code="customer_not_found", message="Customer not found", http_status=404)
        if customer.status == CustomerStatus.DELETED:
            raise AppException(code="party_deleted", message="Customer is deleted", http_status=409)
        if customer.status == CustomerStatus.INACTIVE:
            raise AppException(code="party_inactive", message="Customer is inactive", http_status=409)
        return
    if normalized == "supplier":
        await supplier_service.validate_can_receive_movements(session, tenant_id, party_id)
        return
    if normalized in {"employee", "worker"}:
        await employee_service.validate_can_receive_movements(session, tenant_id, party_id)


async def _post_treasury_movement(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    movement_type: MovementType,
    direction: Literal["in", "out"],
    amount: Decimal,
    lines: list[dict[str, Any]],
    reference_type: str,
    reference_id: UUID,
    description: str | None,
    entry_date: date | None,
    actor_id: UUID | None,
    treasury_id: UUID | None = None,
    party_type: str | None = None,
    party_id: UUID | None = None,
    commit: bool = True,
) -> TreasuryTransaction:
    if amount <= 0:
        raise AppException(
            code="treasury_amount_invalid",
            message="Amount must be greater than zero",
            http_status=422,
        )
    await _assert_party_active(session, tenant_id, party_type=party_type, party_id=party_id)
    tx_date = entry_date or date.today()
    payload = RecordFinancialTransactionInput(
        tenant_id=tenant_id,
        actor_id=actor_id,
        date=tx_date,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        lines=[
            {
                **line,
                "debit": Decimal(str(line.get("debit") or 0)),
                "credit": Decimal(str(line.get("credit") or 0)),
                "reference_type": line.get("reference_type") or reference_type,
                "reference_id": line.get("reference_id") or reference_id,
            }
            for line in lines
        ],
        treasury_movement=TreasuryMovementInput(
            treasury_id=treasury_id,
            amount=amount,
            direction=direction,
            reference_type=reference_type,
            reference_id=reference_id,
            movement_type=movement_type,
            party_type=party_type,
            party_id=party_id,
        ),
    )
    result = await record_financial_transaction(session, payload, commit=commit)
    if not result.treasury_transaction_id:
        raise AppException(
            code="treasury_transaction_missing",
            message="Treasury transaction was not created",
            http_status=500,
        )
    tx = await session.get(TreasuryTransaction, result.treasury_transaction_id)
    if not tx:
        raise AppException(
            code="treasury_transaction_not_found",
            message="Treasury transaction created but not returned",
            http_status=500,
        )
    await audit_log_service.record_audit_log(
        session,
        tenant_id,
        "treasury_transactions",
        str(tx.id),
        "treasury_transaction_create",
        user_id=actor_id,
        new_data={
            "movement_type": movement_type,
            "amount": str(tx.amount),
            "direction": tx.direction,
            "reference_type": reference_type,
            "reference_id": str(reference_id),
            "party_type": party_type,
            "party_id": str(party_id) if party_id else None,
        },
        commit=commit,
    )
    return tx


async def create_receipt(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    amount: Decimal | str | int | float,
    customer_id: UUID,
    reference_type: str | None = None,
    reference_id: UUID,
    description: str | None = None,
    entry_date: date | None = None,
    treasury_id: UUID | None = None,
    actor_id: UUID | None = None,
    commit: bool = True,
) -> TreasuryTransaction:
    if not customer_id:
        raise AppException(code="customer_required", message="Customer is required", http_status=422)
    mapping = await validate_tenant_account_mapping(
        session,
        tenant_id,
        ACCOUNT_MAPPING_REQUIREMENTS["treasury_receipt"],
    )
    cash_account = _select_cash_account(mapping)
    if not cash_account:
        raise AppException(
            code="cash_account_missing",
            message="Cash/bank account mapping is required",
            http_status=422,
        )
    ar_account = mapping["accounts_receivable_account_id"]
    if not ar_account:
        raise AppException(
            code="accounts_receivable_missing",
            message="Accounts receivable mapping is required",
            http_status=422,
        )
    amt = _quantize(amount)
    ref_type = reference_type or "payment"
    lines = [
        {
            "account_id": cash_account,
            "debit": amt,
            "credit": Decimal("0"),
            "entity_type": "client",
            "entity_id": customer_id,
            "line_description": description or f"Receipt {reference_id}",
        },
        {
            "account_id": ar_account,
            "debit": Decimal("0"),
            "credit": amt,
            "entity_type": "client",
            "entity_id": customer_id,
            "line_description": description or f"Receipt {reference_id}",
        },
    ]
    return await _post_treasury_movement(
        session,
        tenant_id,
        movement_type="receipt",
        direction="in",
        amount=amt,
        lines=lines,
        reference_type=ref_type,
        reference_id=reference_id,
        description=description or f"Receipt {reference_id}",
        entry_date=entry_date,
        actor_id=actor_id,
        treasury_id=treasury_id,
        party_type="client",
        party_id=customer_id,
        commit=commit,
    )


async def create_supplier_payment(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    amount: Decimal | str | int | float,
    supplier_id: UUID,
    reference_type: str | None = None,
    reference_id: UUID,
    description: str | None = None,
    entry_date: date | None = None,
    treasury_id: UUID | None = None,
    actor_id: UUID | None = None,
    commit: bool = True,
) -> TreasuryTransaction:
    if not supplier_id:
        raise AppException(code="supplier_required", message="Supplier is required", http_status=422)
    mapping = await validate_tenant_account_mapping(
        session,
        tenant_id,
        ACCOUNT_MAPPING_REQUIREMENTS["treasury_supplier_payment"],
    )
    cash_account = _select_cash_account(mapping)
    if not cash_account:
        raise AppException(
            code="cash_account_missing",
            message="Cash/bank account mapping is required",
            http_status=422,
        )
    payables_account = mapping["payables_account_id"]
    if not payables_account:
        raise AppException(
            code="payables_missing",
            message="Payables account mapping is required",
            http_status=422,
        )
    amt = _quantize(amount)
    ref_type = reference_type or "supplier_payment"
    lines = [
        {
            "account_id": payables_account,
            "debit": amt,
            "credit": Decimal("0"),
            "entity_type": "supplier",
            "entity_id": supplier_id,
            "line_description": description or f"Supplier payment {reference_id}",
        },
        {
            "account_id": cash_account,
            "debit": Decimal("0"),
            "credit": amt,
            "entity_type": "supplier",
            "entity_id": supplier_id,
            "line_description": description or f"Supplier payment {reference_id}",
        },
    ]
    return await _post_treasury_movement(
        session,
        tenant_id,
        movement_type="supplier_payment",
        direction="out",
        amount=amt,
        lines=lines,
        reference_type=ref_type,
        reference_id=reference_id,
        description=description or f"Supplier payment {reference_id}",
        entry_date=entry_date,
        actor_id=actor_id,
        treasury_id=treasury_id,
        party_type="supplier",
        party_id=supplier_id,
        commit=commit,
    )


async def create_expense(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    amount: Decimal | str | int | float,
    supplier_id: UUID,
    reference_type: str | None = None,
    reference_id: UUID,
    description: str | None = None,
    entry_date: date | None = None,
    treasury_id: UUID | None = None,
    actor_id: UUID | None = None,
    commit: bool = True,
) -> TreasuryTransaction:
    if not supplier_id:
        raise AppException(code="supplier_required", message="Supplier is required", http_status=422)
    mapping = await validate_tenant_account_mapping(
        session,
        tenant_id,
        ACCOUNT_MAPPING_REQUIREMENTS["treasury_expense"],
    )
    cash_account = _select_cash_account(mapping)
    if not cash_account:
        raise AppException(
            code="cash_account_missing",
            message="Cash/bank account mapping is required",
            http_status=422,
        )
    expense_account = mapping["expense_account_id"]
    if not expense_account:
        raise AppException(
            code="expense_account_missing",
            message="Expense account mapping is required",
            http_status=422,
        )
    amt = _quantize(amount)
    ref_type = reference_type or "expense"
    lines = [
        {
            "account_id": expense_account,
            "debit": amt,
            "credit": Decimal("0"),
            "entity_type": "supplier",
            "entity_id": supplier_id,
            "line_description": description or f"Expense {reference_id}",
        },
        {
            "account_id": cash_account,
            "debit": Decimal("0"),
            "credit": amt,
            "entity_type": "supplier",
            "entity_id": supplier_id,
            "line_description": description or f"Expense {reference_id}",
        },
    ]
    return await _post_treasury_movement(
        session,
        tenant_id,
        movement_type="expense",
        direction="out",
        amount=amt,
        lines=lines,
        reference_type=ref_type,
        reference_id=reference_id,
        description=description or f"Expense {reference_id}",
        entry_date=entry_date,
        actor_id=actor_id,
        treasury_id=treasury_id,
        party_type="supplier",
        party_id=supplier_id,
        commit=commit,
    )


async def create_payroll_payout(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    amount: Decimal | str | int | float,
    employee_id: UUID,
    reference_type: str | None = None,
    reference_id: UUID,
    description: str | None = None,
    entry_date: date | None = None,
    treasury_id: UUID | None = None,
    actor_id: UUID | None = None,
    commit: bool = True,
) -> TreasuryTransaction:
    if not employee_id:
        raise AppException(code="employee_required", message="Employee is required", http_status=422)
    mapping = await validate_tenant_account_mapping(
        session,
        tenant_id,
        ACCOUNT_MAPPING_REQUIREMENTS["treasury_payroll_payout"],
    )
    cash_account = _select_cash_account(mapping)
    if not cash_account:
        raise AppException(
            code="cash_account_missing",
            message="Cash/bank account mapping is required",
            http_status=422,
        )
    expense_account = mapping["expense_account_id"]
    if not expense_account:
        raise AppException(
            code="expense_account_missing",
            message="Expense account mapping is required",
            http_status=422,
        )
    amt = _quantize(amount)
    ref_type = reference_type or "payroll_payout"
    lines = [
        {
            "account_id": expense_account,
            "debit": amt,
            "credit": Decimal("0"),
            "entity_type": "worker",
            "entity_id": employee_id,
            "line_description": description or f"Payroll payout {reference_id}",
        },
        {
            "account_id": cash_account,
            "debit": Decimal("0"),
            "credit": amt,
            "entity_type": "worker",
            "entity_id": employee_id,
            "line_description": description or f"Payroll payout {reference_id}",
        },
    ]
    return await _post_treasury_movement(
        session,
        tenant_id,
        movement_type="payroll_payout",
        direction="out",
        amount=amt,
        lines=lines,
        reference_type=ref_type,
        reference_id=reference_id,
        description=description or f"Payroll payout {reference_id}",
        entry_date=entry_date,
        actor_id=actor_id,
        treasury_id=treasury_id,
        party_type="worker",
        party_id=employee_id,
        commit=commit,
    )


async def create_employee_payment(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    amount: Decimal | str | int | float,
    employee_id: UUID,
    reference_type: str | None = None,
    reference_id: UUID,
    description: str | None = None,
    entry_date: date | None = None,
    treasury_id: UUID | None = None,
    actor_id: UUID | None = None,
    commit: bool = True,
) -> TreasuryTransaction:
    if not employee_id:
        raise AppException(code="employee_required", message="Employee is required", http_status=422)
    mapping = await validate_tenant_account_mapping(
        session,
        tenant_id,
        ACCOUNT_MAPPING_REQUIREMENTS["treasury_employee_payment"],
    )
    cash_account = _select_cash_account(mapping)
    if not cash_account:
        raise AppException(
            code="cash_account_missing",
            message="Cash/bank account mapping is required",
            http_status=422,
        )
    expense_account = mapping["expense_account_id"]
    if not expense_account:
        raise AppException(
            code="expense_account_missing",
            message="Expense account mapping is required",
            http_status=422,
        )
    amt = _quantize(amount)
    ref_type = reference_type or "employee_payment"
    lines = [
        {
            "account_id": expense_account,
            "debit": amt,
            "credit": Decimal("0"),
            "entity_type": "worker",
            "entity_id": employee_id,
            "line_description": description or f"Employee payment {reference_id}",
        },
        {
            "account_id": cash_account,
            "debit": Decimal("0"),
            "credit": amt,
            "entity_type": "worker",
            "entity_id": employee_id,
            "line_description": description or f"Employee payment {reference_id}",
        },
    ]
    return await _post_treasury_movement(
        session,
        tenant_id,
        movement_type="employee_payment",
        direction="out",
        amount=amt,
        lines=lines,
        reference_type=ref_type,
        reference_id=reference_id,
        description=description or f"Employee payment {reference_id}",
        entry_date=entry_date,
        actor_id=actor_id,
        treasury_id=treasury_id,
        party_type="worker",
        party_id=employee_id,
        commit=commit,
    )


async def create_disbursement(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    amount: Decimal | str | int | float,
    counterparty_account_id: UUID,
    reference_type: str | None = None,
    reference_id: UUID,
    description: str | None = None,
    entry_date: date | None = None,
    treasury_id: UUID | None = None,
    actor_id: UUID | None = None,
    counterparty_entity_type: str | None = None,
    counterparty_entity_id: UUID | None = None,
    commit: bool = True,
) -> TreasuryTransaction:
    if not counterparty_account_id:
        raise AppException(
            code="counterparty_account_required",
            message="Counterparty account is required",
            http_status=422,
        )
    mapping = await validate_tenant_account_mapping(
        session,
        tenant_id,
        ACCOUNT_MAPPING_REQUIREMENTS["treasury_disbursement"],
    )
    cash_account = _select_cash_account(mapping)
    if not cash_account:
        raise AppException(
            code="cash_account_missing",
            message="Cash/bank account mapping is required",
            http_status=422,
        )
    amt = _quantize(amount)
    ref_type = reference_type or "treasury_disbursement"
    lines = [
        {
            "account_id": counterparty_account_id,
            "debit": amt,
            "credit": Decimal("0"),
            "entity_type": counterparty_entity_type,
            "entity_id": counterparty_entity_id,
            "line_description": description or f"Disbursement {reference_id}",
        },
        {
            "account_id": cash_account,
            "debit": Decimal("0"),
            "credit": amt,
            "entity_type": counterparty_entity_type,
            "entity_id": counterparty_entity_id,
            "line_description": description or f"Disbursement {reference_id}",
        },
    ]
    return await _post_treasury_movement(
        session,
        tenant_id,
        movement_type="disbursement",
        direction="out",
        amount=amt,
        lines=lines,
        reference_type=ref_type,
        reference_id=reference_id,
        description=description or f"Disbursement {reference_id}",
        entry_date=entry_date,
        actor_id=actor_id,
        treasury_id=treasury_id,
        party_type=counterparty_entity_type,
        party_id=counterparty_entity_id,
        commit=commit,
    )


__all__ = [
    "create_receipt",
    "create_supplier_payment",
    "create_expense",
    "create_payroll_payout",
    "create_employee_payment",
    "create_disbursement",
]
