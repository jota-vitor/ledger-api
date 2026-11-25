import pytest

from app.domain import (
    InsufficientFunds,
    InvalidAmount,
    SameAccount,
    fingerprint,
    format_brl,
    validate_transfer,
)


def test_valid_transfer_passes():
    validate_transfer(from_id=1, to_id=2, from_balance=1000, amount_cents=1000)


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"from_id": 1, "to_id": 1, "from_balance": 500, "amount_cents": 100}, SameAccount),
        ({"from_id": 1, "to_id": 2, "from_balance": 500, "amount_cents": 0}, InvalidAmount),
        ({"from_id": 1, "to_id": 2, "from_balance": 500, "amount_cents": -5}, InvalidAmount),
        ({"from_id": 1, "to_id": 2, "from_balance": 99, "amount_cents": 100}, InsufficientFunds),
    ],
)
def test_invalid_transfers(kwargs, error):
    with pytest.raises(error):
        validate_transfer(**kwargs)


def test_fingerprint_ignores_key_order():
    assert fingerprint({"a": 1, "b": 2}) == fingerprint({"b": 2, "a": 1})


def test_fingerprint_changes_with_payload():
    assert fingerprint({"amount": 100}) != fingerprint({"amount": 101})


@pytest.mark.parametrize(
    ("cents", "expected"),
    [(0, "R$ 0,00"), (5, "R$ 0,05"), (123456, "R$ 1.234,56"), (-2590, "-R$ 25,90")],
)
def test_format_brl(cents, expected):
    assert format_brl(cents) == expected
