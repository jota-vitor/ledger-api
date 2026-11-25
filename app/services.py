from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain import (
    AccountNotFound,
    IdempotencyConflict,
    fingerprint,
    validate_amount,
    validate_transfer,
)
from app.models import Account, LedgerEntry, Operation, OperationKind


def create_account(db: Session, owner_name: str) -> Account:
    account = Account(owner_name=owner_name, balance_cents=0)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def get_account(db: Session, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise AccountNotFound(f"Conta {account_id} não encontrada")
    return account


def _lock_accounts(db: Session, account_ids: set[int]) -> dict[int, Account]:
    # Trava as linhas sempre na mesma ordem (por id). Duas transferências cruzadas
    # A->B e B->A pedem as travas na mesma sequência, então não dá deadlock.
    rows = db.scalars(
        select(Account)
        .where(Account.id.in_(sorted(account_ids)))
        .order_by(Account.id)
        .with_for_update()
    ).all()
    accounts = {account.id: account for account in rows}
    for account_id in account_ids:
        if account_id not in accounts:
            raise AccountNotFound(f"Conta {account_id} não encontrada")
    return accounts


def _find_previous(db: Session, key: str, request_hash: str) -> Operation | None:
    previous = db.scalar(select(Operation).where(Operation.idempotency_key == key))
    if previous is None:
        return None
    if previous.request_fingerprint != request_hash:
        raise IdempotencyConflict("Esta Idempotency-Key já foi usada com outros dados")
    return previous


def _post(db: Session, account: Account, operation: Operation, amount_cents: int) -> None:
    account.balance_cents += amount_cents
    db.add(
        LedgerEntry(
            account_id=account.id,
            operation=operation,
            amount_cents=amount_cents,
            balance_after_cents=account.balance_cents,
        )
    )


def _commit(db: Session, operation: Operation, key: str, request_hash: str):
    try:
        db.commit()
    except IntegrityError:
        # Outra requisição com a mesma chave terminou primeiro: devolvemos o resultado dela.
        db.rollback()
        previous = _find_previous(db, key, request_hash)
        if previous is None:
            raise
        return previous, True
    db.refresh(operation)
    return operation, False


def deposit(
    db: Session, account_id: int, amount_cents: int, key: str, description: str | None
) -> tuple[Operation, bool]:
    request_hash = fingerprint(
        {"kind": "deposit", "to": account_id, "amount": amount_cents, "desc": description}
    )
    if previous := _find_previous(db, key, request_hash):
        return previous, True

    validate_amount(amount_cents)
    account = _lock_accounts(db, {account_id})[account_id]

    operation = Operation(
        kind=OperationKind.deposit,
        idempotency_key=key,
        request_fingerprint=request_hash,
        to_account_id=account_id,
        amount_cents=amount_cents,
        description=description,
    )
    db.add(operation)
    _post(db, account, operation, amount_cents)
    return _commit(db, operation, key, request_hash)


def transfer(
    db: Session,
    from_id: int,
    to_id: int,
    amount_cents: int,
    key: str,
    description: str | None,
) -> tuple[Operation, bool]:
    request_hash = fingerprint(
        {
            "kind": "transfer",
            "from": from_id,
            "to": to_id,
            "amount": amount_cents,
            "desc": description,
        }
    )
    if previous := _find_previous(db, key, request_hash):
        return previous, True

    accounts = _lock_accounts(db, {from_id, to_id})
    validate_transfer(from_id, to_id, accounts[from_id].balance_cents, amount_cents)

    operation = Operation(
        kind=OperationKind.transfer,
        idempotency_key=key,
        request_fingerprint=request_hash,
        from_account_id=from_id,
        to_account_id=to_id,
        amount_cents=amount_cents,
        description=description,
    )
    db.add(operation)
    _post(db, accounts[from_id], operation, -amount_cents)
    _post(db, accounts[to_id], operation, amount_cents)
    return _commit(db, operation, key, request_hash)


def statement(db: Session, account_id: int, offset: int, limit: int):
    get_account(db, account_id)
    base = select(LedgerEntry).where(LedgerEntry.account_id == account_id)
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    entries = db.scalars(base.order_by(LedgerEntry.id.desc()).offset(offset).limit(limit)).all()
    return entries, total


def reconcile(db: Session, account_id: int) -> dict:
    account = get_account(db, account_id)
    ledger_sum = db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount_cents), 0)).where(
            LedgerEntry.account_id == account_id
        )
    )
    return {
        "account_id": account_id,
        "balance_cents": account.balance_cents,
        "ledger_sum_cents": ledger_sum,
        "consistent": account.balance_cents == ledger_sum,
    }
