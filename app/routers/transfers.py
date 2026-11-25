from fastapi import APIRouter, HTTPException, Response, status

from app import services
from app.deps import DbSession, IdempotencyKey
from app.models import Operation
from app.schemas import OperationOut, TransferIn

router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.post("", response_model=OperationOut, status_code=status.HTTP_201_CREATED)
def create_transfer(data: TransferIn, key: IdempotencyKey, db: DbSession, response: Response):
    operation, replayed = services.transfer(
        db,
        data.from_account_id,
        data.to_account_id,
        data.amount_cents,
        key,
        data.description,
    )
    if replayed:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replayed"] = "true"
    return operation


@router.get("/{operation_id}", response_model=OperationOut)
def get_transfer(operation_id: str, db: DbSession):
    operation = db.get(Operation, operation_id)
    if operation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Operação não encontrada")
    return operation
