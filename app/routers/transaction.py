import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import Transaction, TransactionRead
from app.services.screening_stub import screen

router = APIRouter(prefix="/transactions", tags=["transactions"])

# This function will be called by the Gateway service using the URL endpoint
@router.post("", status_code=201, response_model=TransactionRead)
async def create_transaction(
    payload: Transaction, db: AsyncSession = Depends(get_db)
) -> TransactionRead:
    txn = Transaction(
        end_to_end_id=payload.endToEndId,
        debtor_name=payload.debtor.name,
        debtor_agent_bic=payload.debtor.agentBic,
        creditor_name=payload.creditor.name,
        creditor_agent_bic=payload.creditor.agentBic,
        instructed_amount=payload.instructedAmount.amount,
        instructed_currency=payload.instructedAmount.currency,
        remittance_information=payload.remittanceInformation,
        status="pending",
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    # Now the Result will be taken from the Screening Service once the Transaction has been committed to the DB
    result = screen(payload.debtor.name, payload.creditor.name)
    txn.status = result.status
    txn.screening_ref = result.screening_ref
    await db.commit()
    await db.refresh(txn)

    return TransactionRead.from_model(txn)

# This function will be called by the Gateway service using the URL endpoint for get transaction
@router.get("/{transaction_id}", response_model=TransactionRead)
async def get_transaction(
    transaction_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> TransactionRead:
    txn = await db.get(Transaction, transaction_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="transaction not found")
    return TransactionRead.from_model(txn)