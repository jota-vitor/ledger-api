from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, engine
from app.domain import DomainError
from app.routers import accounts, transfers


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Carteira digital com transferências idempotentes e extrato em partidas dobradas.",
    lifespan=lifespan,
)

app.include_router(accounts.router)
app.include_router(transfers.router)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.message, "code": exc.code}
    )


@app.get("/health", tags=["infra"])
def health():
    return {"status": "ok"}
