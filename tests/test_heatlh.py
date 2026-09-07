from collections.abc import AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.database import Base, get_db
from app.main import app
from app.models import transaction
 
# SQLLite is being used for testing purposes
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)
 
 
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
 
 
app.dependency_overrides[get_db] = override_get_db
 
client = TestClient(app)
 
def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}