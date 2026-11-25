from fastapi import APIRouter, Response, status

from app import services
from app.deps import DbSession, IdempotencyKey, PageParams
from app.schemas import (
    AccountCreate,
    AccountOut,
    DepositIn,
    EntryOut,
    OperationOut,
    Page,
    Reconciliation,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(data: AccountCreate, db: DbSession):
    return services.create_account(db, data.owner_name)


@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, db: DbSession):
    return services.get_account(db, account_id)


@router.post(
    "/{account_id}/deposits", response_model=OperationOut, status_code=status.HTTP_201_CREATED
)
def deposit(
    account_id: int, data: DepositIn, key: IdempotencyKey, db: DbSession, response: Response
):
    operation, replayed = services.deposit(db, account_id, data.amount_cents, key, data.description)
    if replayed:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replayed"] = "true"
    return operation


@router.get("/{account_id}/statement", response_model=Page[EntryOut])
def statement(account_id: int, db: DbSession, pagination: PageParams):
    entries, total = services.statement(db, account_id, pagination.offset, pagination.size)
    return Page[EntryOut](items=entries, total=total, page=pagination.page, size=pagination.size)


@router.get("/{account_id}/reconciliation", response_model=Reconciliation)
def reconciliation(account_id: int, db: DbSession):
    return services.reconcile(db, account_id)
