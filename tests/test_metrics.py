from collections.abc import AsyncGenerator

import httpx
import respx
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import transaction  # noqa: F401  (registers the table)
from app.services import sqs_publisher

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
PAYLOAD = {
    "endToEndId": "REF20261106001",
    "debtor": {"name": "Acme Exports Ltd"},
    "creditor": {"name": "Example Trading Co"},
    "instructedAmount": {"amount": "1000.00", "currency": "USD"},
}


def sample(name, **labels):
    # Counters are process-wide, so tests compare before/after instead of absolute values
    return REGISTRY.get_sample_value(name, labels) or 0.0


def mock_screening(verdict, matched_entity=None):
    respx.post(SCREENING_URL).mock(
        return_value=httpx.Response(
            200, json={"verdict": verdict, "matchedEntity": matched_entity, "screeningRef": "SCR-TEST-1"}
        )
    )


class FailingSQS:
    def send_message(self, **kwargs):
        raise RuntimeError("sqs unavailable")


@respx.mock
def test_request_is_counted_by_route_template_and_status():
    mock_screening("clear")
    labels = {"method": "POST", "route": "/transactions", "status": "201"}
    before = sample("http_requests_total", **labels)

    assert client.post("/transactions", json=PAYLOAD).status_code == 201

    assert sample("http_requests_total", **labels) == before + 1
    body = client.get("/metrics").text
    assert 'route="/healthz"' not in body


def test_lookups_share_the_template_label():
    labels = {"method": "GET", "route": "/transactions/{transaction_id}", "status": "404"}
    before = sample("http_requests_total", **labels)
    unknown = "00000000-0000-0000-0000-000000000001"

    assert client.get(f"/transactions/{unknown}").status_code == 404

    assert sample("http_requests_total", **labels) == before + 1
    assert unknown not in client.get("/metrics").text


@respx.mock
def test_screening_verdicts_are_counted():
    mock_screening("clear")
    clear_before = sample("transactions_screened_total", verdict="clear")
    client.post("/transactions", json={**PAYLOAD, "endToEndId": "REF20261106002"})
    assert sample("transactions_screened_total", verdict="clear") == clear_before + 1


@respx.mock
def test_failed_alert_publish_is_counted_and_returns_502(monkeypatch):
    monkeypatch.setattr(settings, "sqs_queue_url", "https://sqs.us-west-2.amazonaws.com/123/queue")
    monkeypatch.setattr(sqs_publisher, "_client", lambda: FailingSQS())
    mock_screening("flagged", "NORTHWIND TRADING CONSORTIUM")
    failures_before = sample("sqs_publish_failures_total")
    flagged_before = sample("transactions_screened_total", verdict="flagged")
    errors_before = sample("http_requests_total", method="POST", route="/transactions", status="502")

    resp = client.post("/transactions", json={**PAYLOAD, "endToEndId": "REF20261106003"})

    assert resp.status_code == 502
    assert sample("sqs_publish_failures_total") == failures_before + 1
    assert sample("transactions_screened_total", verdict="flagged") == flagged_before + 1
    assert sample("http_requests_total", method="POST", route="/transactions", status="502") == errors_before + 1


def test_metrics_endpoint_serves_prometheus_text_with_the_slo_bucket():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert 'le="0.3"' in response.text
