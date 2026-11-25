from typing import Annotated

from fastapi import Depends, Header, Query
from sqlalchemy.orm import Session

from app.database import get_db

DbSession = Annotated[Session, Depends(get_db)]

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=100,
        description="Identificador único da operação, gerado pelo cliente (ex.: um UUID).",
    ),
]


class Pagination:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1, le=100)] = 20,
    ):
        self.page = page
        self.size = size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


PageParams = Annotated[Pagination, Depends()]
