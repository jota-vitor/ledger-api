import os
import uuid

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def new_account(client):
    def _create(name: str = "Ana", initial_cents: int = 0) -> int:
        account_id = client.post("/accounts", json={"owner_name": name}).json()["id"]
        if initial_cents:
            client.post(
                f"/accounts/{account_id}/deposits",
                json={"amount_cents": initial_cents},
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
        return account_id

    return _create


def key() -> dict:
    return {"Idempotency-Key": str(uuid.uuid4())}
