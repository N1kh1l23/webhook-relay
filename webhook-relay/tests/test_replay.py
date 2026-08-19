import pytest
import httpx
from httpx import AsyncClient

class FakeResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text

async def fake_post_success(self, *args, **kwargs):
    return FakeResponse(200, "ok")

async def fake_post_fail(self, *args, **kwargs):
    return FakeResponse(500, "yes")

async def fake_post_timeout(self, *args, **kwargs):
    raise httpx.TimeoutException("No response exists")

@pytest.mark.asyncio
async def test_replay_success(client: AsyncClient, monkeypatch):
    source_response = await client.post("/sources", json={"name": "replay-test"})
    source_data = source_response.json()
    new_token = source_data["token"]

    event_response = await client.post(f"/in/{new_token}", json={"event": "test"})
    event_data = event_response.json()
    event_id = event_data["event_id"]

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post_success)

    response = await client.post(
        f"/events/{event_id}/replay", json = {"destination_url": "https://hi.com/yo"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "delivered"
    assert data["response_status"] == 200
   
