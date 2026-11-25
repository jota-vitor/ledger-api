import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OperationKind(enum.StrEnum):
    deposit = "deposit"
    transfer = "transfer"


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (CheckConstraint("balance_cents >= 0", name="ck_balance_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_name: Mapped[str] = mapped_column(String(120))
    balance_cents: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Operation(Base):
    """Uma movimentação (depósito ou transferência). Gera um ou dois lançamentos."""

    __tablename__ = "operations"
    __table_args__ = (CheckConstraint("amount_cents > 0", name="ck_amount_positive"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kind: Mapped[OperationKind] = mapped_column(Enum(OperationKind, native_enum=False))
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    from_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    to_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    amount_cents: Mapped[int]
    description: Mapped[str | None] = mapped_column(String(140))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LedgerEntry(Base):
    """Lançamento no extrato: negativo é débito, positivo é crédito."""

    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    operation_id: Mapped[str] = mapped_column(ForeignKey("operations.id"), index=True)
    amount_cents: Mapped[int]
    balance_after_cents: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    operation: Mapped[Operation] = relationship()
