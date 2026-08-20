import pytest
import uuid
import httpx
from httpx import AsyncClient
from app.routes import replay

class FakeResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text

class ClientReplacement:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def post(self, url, *args, **kwargs):
        return FakeResponse(200, "ok")

    async def __aexit__(self, exc_type, exc, tb):
        pass

class ClientReplacementFail:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def post(self, url, *args, **kwargs):
        return FakeResponse(500, "yes")

    async def __aexit__(self, exc_type, exc, tb):
        pass

class ClientTimeout :
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def post(self, url, *args, **kwargs):
        raise httpx.TimeoutException("No response exists")

    async def __aexit__(self, exc_type, exc, tb):
        pass

@pytest.mark.asyncio
async def test_replay_success(client: AsyncClient, monkeypatch):
    source_response = await client.post("/sources", json={"name": "replay-test"})
    source_data = source_response.json()
    new_token = source_data["token"]

    event_response = await client.post(f"/in/{new_token}", json={"event": "test"})
    event_data = event_response.json()
    event_id = event_data["event_id"]

    monkeypatch.setattr(replay, "AsyncClient", ClientReplacement)

    response = await client.post(
        f"/events/{event_id}/replay", json = {"destination_url": "https://hi.com/yo"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "delivered"
    assert data["response_status"] == 200

@pytest.mark.asyncio
async def test_replay_failure(client: AsyncClient, monkeypatch):
    source_response = await client.post("/sources", json={"name": "replay-test"})
    source_data = source_response.json()
    new_token = source_data["token"]

    event_response = await client.post(f"/in/{new_token}", json={"event": "test"})
    event_data = event_response.json()
    event_id = event_data["event_id"]

    monkeypatch.setattr(replay, "AsyncClient", ClientReplacementFail)

    response = await client.post(
        f"/events/{event_id}/replay", json = {"destination_url": "https://hi.com/yo"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["response_status"] == 500

@pytest.mark.asyncio
async def test_replay_timeout(client: AsyncClient, monkeypatch):
    source_response = await client.post("/sources", json={"name": "replay-test"})
    source_data = source_response.json()
    new_token = source_data["token"]

    event_response = await client.post(f"/in/{new_token}", json={"event": "test"})
    event_data = event_response.json()
    event_id = event_data["event_id"]

    monkeypatch.setattr(replay, "AsyncClient", ClientTimeout)

    response = await client.post(
        f"/events/{event_id}/replay", json = {"destination_url": "https://hi.com/yo"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["response_status"] is None


@pytest.mark.asyncio
async def test_list_attempts(client: AsyncClient, monkeypatch):
    source_response = await client.post("/sources", json={"name": "replay-test"})
    source_data = source_response.json()
    new_token = source_data["token"]

    event_response = await client.post(f"/in/{new_token}", json={"event": "test"})
    event_data = event_response.json()
    event_id = event_data["event_id"]

    monkeypatch.setattr(replay, "AsyncClient", ClientReplacement)

    for x in range(2):
        await client.post(f"/events/{event_id}/replay", json = {"destination_url": "https://hi.com/yo"})

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
