import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
 
 
class Transaction(Base): 
    __tablename__ = "transactions"
 
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    end_to_end_id: Mapped[str] = mapped_column(String, nullable=False)
 
    debtor_name: Mapped[str] = mapped_column(String, nullable=False)
    #Debtor BIC is Optional in MT103
    debtor_agent_bic: Mapped[str | None] = mapped_column(String(11), nullable=True)
 
    creditor_name: Mapped[str] = mapped_column(String, nullable=False)
    #Creditor BIC is Optional in MT103
    creditor_agent_bic: Mapped[str | None] = mapped_column(String(11), nullable=True)
 

    instructed_amount: Mapped[str] = mapped_column(String, nullable=False)
    instructed_currency: Mapped[str] = mapped_column(String(3), nullable=False)
 
    remittance_information: Mapped[str | None] = mapped_column(String, nullable=True)
 
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    screening_ref: Mapped[str | None] = mapped_column(String, nullable=True)
 
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )