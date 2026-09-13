from collections.abc import AsyncGenerator
 
import httpx
import respx
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
 
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import transaction  

test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)
 
 
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
 
 
app.dependency_overrides[get_db] = override_get_db
 
client = TestClient(app)

SCREENING_URL = f"{settings.screening_service_url}/screen"
 
VALID_PAYLOAD = {
    "endToEndId": "REF20260907001",
    "debtor": {"name": "Acme Exports Ltd"},
    "creditor": {"name": "Example Trading Co"},
    "instructedAmount": {"amount": "1000.00", "currency": "USD"},
}
 
 
@respx.mock
def test_create_transaction_persists_and_returns_full_record():
    respx.post(SCREENING_URL).mock(
        return_value=httpx.Response(
            200,
            json={"verdict": "clear", "matchedEntity": None, "screeningRef": "SCR-CLR-a1b2c3d4e5f6"},
        )
    )
    resp = client.post("/transactions", json=VALID_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["endToEndId"] == "REF20260907001"
    assert body["debtor"] == {"name": "Acme Exports Ltd", "agentBic": None}
    assert body["instructedAmount"] == {"amount": "1000.00", "currency": "USD"}
    assert body["status"] == "clear"
    assert body["screeningRef"] == "SCR-CLR-a1b2c3d4e5f6"
    assert body["id"]
    assert body["createdAt"]
 
 
@respx.mock
def test_create_transaction_with_bics_and_remittance():
    respx.post(SCREENING_URL).mock(
        return_value=httpx.Response(
            200,
            json={"verdict": "clear", "matchedEntity": None, "screeningRef": "SCR-CLR-000000000000"},
        )
    )
    payload = {
        **VALID_PAYLOAD,
        "endToEndId": "REF20260907002",
        "debtor": {"name": "Acme Exports Ltd", "agentBic": "DEUTDEFF"},
        "creditor": {"name": "Example Trading Co", "agentBic": "CHASUS33XXX"},
        "remittanceInformation": "Invoice 4521",
    }
    resp = client.post("/transactions", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["debtor"]["agentBic"] == "DEUTDEFF"
    assert body["creditor"]["agentBic"] == "CHASUS33XXX"
    assert body["remittanceInformation"] == "Invoice 4521"
 
 
def test_create_transaction_rejects_bad_bic_length():
    payload = {**VALID_PAYLOAD, "debtor": {"name": "Acme Exports Ltd", "agentBic": "SHORT"}}
    resp = client.post("/transactions", json=payload)
    assert resp.status_code == 422
    assert resp.json()["error"] == "validation_error"
 
 
@respx.mock
def test_create_transaction_flagged_by_screening():
    respx.post(SCREENING_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "verdict": "flagged",
                "matchedEntity": "NORTHWIND TRADING CONSORTIUM",
                "screeningRef": "SCR-SDN-40347",
            },
        )
    )
    payload = {**VALID_PAYLOAD, "endToEndId": "REF20260907004", "debtor": {"name": "NORTHWIND TRADING CO"}}
    resp = client.post("/transactions", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "flagged"
    assert body["screeningRef"] == "SCR-SDN-40347"
 
 
@respx.mock
def test_create_transaction_502_when_screening_unreachable():
    respx.post(SCREENING_URL).mock(side_effect=httpx.ConnectError("connection refused"))
    resp = client.post("/transactions", json={**VALID_PAYLOAD, "endToEndId": "REF20260907005"})
    assert resp.status_code == 502
    assert resp.json() == {"error": "http_error", "message": "screening service unreachable"}
 
 
@respx.mock
def test_get_transaction_returns_created_record():
    respx.post(SCREENING_URL).mock(
        return_value=httpx.Response(
            200,
            json={"verdict": "clear", "matchedEntity": None, "screeningRef": "SCR-CLR-111111111111"},
        )
    )
    create_resp = client.post(
        "/transactions", json={**VALID_PAYLOAD, "endToEndId": "REF20260907003"}
    )
    txn_id = create_resp.json()["id"]
 
    get_resp = client.get(f"/transactions/{txn_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == txn_id
    assert get_resp.json()["endToEndId"] == "REF20260907003"
 
 
def test_get_transaction_404_for_unknown_id():
    resp = client.get("/transactions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    assert resp.json() == {"error": "http_error", "message": "transaction not found"}
 
 
def test_get_transaction_422_for_non_uuid_id():
    resp = client.get("/transactions/not-a-uuid")
    assert resp.status_code == 422
    assert resp.json()["error"] == "validation_error"