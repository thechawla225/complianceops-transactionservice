from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_models
from app.models import transaction  
from app.routers import health
 
 
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    yield
 
 
app = FastAPI(title="ComplianceOps Transaction Service", lifespan=lifespan)
 
app.include_router(health.router)