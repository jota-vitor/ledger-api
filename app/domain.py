"""Regras de negócio puras, sem banco e sem HTTP.

Ficam separadas para serem testadas de forma isolada e reaproveitadas
por qualquer camada (API, worker, script).
"""

import hashlib
import json

MAX_AMOUNT_CENTS = 100_000_000  # R$ 1.000.000,00 por operação


class DomainError(Exception):
    status_code = 422
    code = "domain_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidAmount(DomainError):
    code = "invalid_amount"


class SameAccount(DomainError):
    code = "same_account"


class InsufficientFunds(DomainError):
    code = "insufficient_funds"


class AccountNotFound(DomainError):
    status_code = 404
    code = "account_not_found"


class IdempotencyConflict(DomainError):
    status_code = 409
    code = "idempotency_conflict"


def validate_amount(amount_cents: int) -> None:
    if amount_cents <= 0:
        raise InvalidAmount("O valor precisa ser maior que zero")
    if amount_cents > MAX_AMOUNT_CENTS:
        raise InvalidAmount("Valor acima do limite por operação")


def validate_transfer(from_id: int, to_id: int, from_balance: int, amount_cents: int) -> None:
    if from_id == to_id:
        raise SameAccount("Origem e destino precisam ser contas diferentes")
    validate_amount(amount_cents)
    if from_balance < amount_cents:
        raise InsufficientFunds("Saldo insuficiente")


def fingerprint(payload: dict) -> str:
    """Hash estável do corpo da requisição, usado para checar reuso da Idempotency-Key."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def format_brl(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    reais, centavos = divmod(abs(cents), 100)
    return f"{sign}R$ {reais:,}".replace(",", ".") + f",{centavos:02d}"
