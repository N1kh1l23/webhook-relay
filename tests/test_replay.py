import uuid

import httpx
import pytest
from httpx import AsyncClient

from app.services import delivery
from app.services.delivery import deliver_event


class ClientReplacement:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def post(self, url, *args, **kwargs):
        return httpx.Response(200, text="ok")

    async def __aexit__(self, exc_type, exc, tb):
        pass


@pytest.mark.asyncio
async def test_list_attempts(db, client: AsyncClient, monkeypatch):
    source_response = await client.post("/sources", json={"name": "replay-test"})
    source_data = source_response.json()
    new_token = source_data["token"]

    event_response = await client.post(f"/in/{new_token}", json={"event": "test"})
    event_data = event_response.json()
    event_id = event_data["event_id"]

    monkeypatch.setattr(delivery, "AsyncClient", ClientReplacement)

    for x in range(2):
        await deliver_event(db, event_id, "https://hi.com/yo")

    response = await client.get(f"/events/{event_id}/attempts")

    data = response.json()
    assert response.status_code == 200
    assert len(data) == 2
    assert data[0]["attempt_number"] == 1
    assert data[1]["attempt_number"] == 2

@pytest.mark.asyncio
async def test_list_attempts_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    fake_response = await client.get(f"/events/{fake_id}/attempts")
    assert fake_response.status_code == 404

@pytest.mark.asyncio
async def test_replay_enqueues_job(client: AsyncClient, fake_redis):
    source_response = await client.post("/sources", json={"name": "replay-test"})
    source_data = source_response.json()
    new_token = source_data["token"]

    event_response = await client.post(f"/in/{new_token}", json={"event": "test"})
    event_data = event_response.json()
    event_id = event_data["event_id"]

    response = await client.post(
        f"/events/{event_id}/replay", json={"destination_url": "https://hi.com/yo"}
    )

    assert response.status_code == 202
    data = response.json()
    assert data["job_id"] == "fake-job-id"
    assert data["event_id"] == event_id
    assert len(fake_redis.enqueued) == 1

@pytest.mark.asyncio
async def test_replay_unknown_event_not_enqueued(client: AsyncClient, fake_redis):
    fake_id = str(uuid.uuid4())
    response = await client.post(
        f"/events/{fake_id}/replay", json={"destination_url": "https://hi.com/yo"}
    )

    assert response.status_code == 404
    assert len(fake_redis.enqueued) == 0
