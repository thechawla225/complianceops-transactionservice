from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Debtor(BaseModel):
    name: str
    agentBic: Optional[str] = Field(default=None, min_length=8, max_length=11)


class Creditor(BaseModel):
    name: str
    agentBic: Optional[str] = Field(default=None, min_length=8, max_length=11)


class InstructedAmount(BaseModel):
    amount: str
    currency: str = Field(min_length=3, max_length=3)


class TransactionCreate(BaseModel):
    endToEndId: str
    debtor: Debtor
    creditor: Creditor
    instructedAmount: InstructedAmount
    remittanceInformation: Optional[str] = None

############################################################### Used the same transaction schema defined in gateway service till this point #################################################################

class TransactionRead(BaseModel):
    id: UUID
    endToEndId: str
    debtor: Debtor
    creditor: Creditor
    instructedAmount: InstructedAmount
    remittanceInformation: Optional[str] = None
    status: str
    screeningRef: Optional[str] = None
    createdAt: datetime

    @classmethod
    def from_model(cls, txn) -> "TransactionRead":
        return cls(
            id=txn.id,
            endToEndId=txn.end_to_end_id,
            debtor=Debtor(name=txn.debtor_name, agentBic=txn.debtor_agent_bic),
            creditor=Creditor(name=txn.creditor_name, agentBic=txn.creditor_agent_bic),
            instructedAmount=InstructedAmount(
                amount=txn.instructed_amount, currency=txn.instructed_currency
            ),
            remittanceInformation=txn.remittance_information,
            status=txn.status,
            screeningRef=txn.screening_ref,
            createdAt=txn.created_at,
        )