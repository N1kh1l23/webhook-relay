import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.delivery_attempt import DeliveryAttempt
from app.models.event import Event
from app.services import delivery
from app.services.delivery import deliver_event
from tests.fakes import (
    ClientInvalidURL,
    ClientReplacement,
    ClientReplacementFail,
    ClientTimeout,
)


@pytest.mark.asyncio
async def test_delivery_success(db, client: AsyncClient, monkeypatch):
    source_response = await client.post("/sources", json={"name": "replay-test"})
    source_data = source_response.json()
    new_token = source_data["token"]

    event_response = await client.post(f"/in/{new_token}", json={"event": "test"})
    event_data = event_response.json()
    event_id = event_data["event_id"]

    monkeypatch.setattr(delivery, "AsyncClient", ClientReplacement)

    await deliver_event(db, event_id, "https://hi.com/yo")

    query = select(DeliveryAttempt).where(DeliveryAttempt.event_id == event_id)
    result = await db.execute(query)
    attempts = list(result.scalars().all())
    assert len(attempts) == 1
    assert attempts[0].response_status == 200

@pytest.mark.asyncio
async def test_delivery_failure(db, client: AsyncClient, monkeypatch):
    source_response = await client.post("/sources", json={"name": "replay-test"})
    source_data = source_response.json()
    new_token = source_data["token"]

    event_response = await client.post(f"/in/{new_token}", json={"event": "test"})
    event_data = event_response.json()
    event_id = event_data["event_id"]

    monkeypatch.setattr(delivery, "AsyncClient", ClientReplacementFail)

    await deliver_event(db, event_id, "https://hi.com/yo")

    query = select(DeliveryAttempt).where(DeliveryAttempt.event_id == event_id)
    result = await db.execute(query)
    attempts = list(result.scalars().all())
    assert len(attempts) == 1
    assert attempts[0].response_status == 500

    event_result_check = await db.execute(select(Event).where(Event.id == event_id))
    event_result = event_result_check.scalar_one_or_none()
    assert event_result.status == "retrying"
    assert attempts[0].outcome == "retry"
    assert attempts[0].error_type is None
    assert attempts[0].next_attempt_at is not None


@pytest.mark.asyncio
async def test_delivery_timeout(db, client: AsyncClient, monkeypatch):
    source_response = await client.post("/sources", json={"name": "replay-test"})
    source_data = source_response.json()
    new_token = source_data["token"]

    event_response = await client.post(f"/in/{new_token}", json={"event": "test"})
    event_data = event_response.json()
    event_id = event_data["event_id"]

    monkeypatch.setattr(delivery, "AsyncClient", ClientTimeout)

    await deliver_event(db, event_id, "https://hi.com/yo")

    query = select(DeliveryAttempt).where(DeliveryAttempt.event_id == event_id)
    result = await db.execute(query)
    attempts = list(result.scalars().all())
    assert len(attempts) == 1
    assert attempts[0].response_status is None

    event_result_check = await db.execute(select(Event).where(Event.id == event_id))
    event_result = event_result_check.scalar_one_or_none()

    assert event_result.status == "retrying"
    assert attempts[0].outcome == "retry"
    assert attempts[0].error_type == "TimeoutException"
    assert attempts[0].next_attempt_at is not None

@pytest.mark.asyncio
async def test_delivery_invalid_url(db, client: AsyncClient, monkeypatch):
    source_response = await client.post("/sources", json={"name": "replay-test"})
    source_data = source_response.json()
    new_token = source_data["token"]

    event_response = await client.post(f"/in/{new_token}", json={"event": "test"})
    event_data = event_response.json()
    event_id = event_data["event_id"]

    monkeypatch.setattr(delivery, "AsyncClient", ClientInvalidURL)

    result = await deliver_event(db, event_id, "https://hi.com/yo")
    query = select(DeliveryAttempt).where(DeliveryAttempt.event_id == event_id)
    attempts_result = await db.execute(query)
    attempts = list(attempts_result.scalars().all())

    assert len(attempts) == 1
    assert attempts[0].response_status is None
    assert attempts[0].outcome == "terminal"
    assert attempts[0].error_type == "InvalidURL"
    assert attempts[0].next_attempt_at is None

    event_result_check = await db.execute(select(Event).where(Event.id == event_id))
    event_result = event_result_check.scalar_one_or_none()
    assert event_result.status == "dead_lettered"
    assert result.should_retry is False
