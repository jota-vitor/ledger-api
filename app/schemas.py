from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.domain import format_brl
from app.models import OperationKind

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


class AccountCreate(BaseModel):
    owner_name: str = Field(min_length=2, max_length=120)


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_name: str
    balance_cents: int
    created_at: datetime

    @computed_field
    @property
    def balance(self) -> str:
        return format_brl(self.balance_cents)


class DepositIn(BaseModel):
    amount_cents: int = Field(gt=0, examples=[15000])
    description: str | None = Field(default=None, max_length=140)


class TransferIn(BaseModel):
    from_account_id: int
    to_account_id: int
    amount_cents: int = Field(gt=0, examples=[2590])
    description: str | None = Field(default=None, max_length=140)


class OperationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: OperationKind
    from_account_id: int | None
    to_account_id: int
    amount_cents: int
    description: str | None
    created_at: datetime


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operation_id: str
    amount_cents: int
    balance_after_cents: int
    created_at: datetime


class Reconciliation(BaseModel):
    account_id: int
    balance_cents: int
    ledger_sum_cents: int
    consistent: bool
