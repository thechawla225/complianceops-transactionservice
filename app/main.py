from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_models
from app.exceptions import register_exception_handlers
from app.models import transaction 
from app.routers import health, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    yield


app = FastAPI(title="ComplianceOps Transaction Service", lifespan=lifespan)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(transactions.router)