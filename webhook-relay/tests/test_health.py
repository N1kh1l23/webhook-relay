import pytest
from httpx import AsyncClient

from app import main


@pytest.mark.asyncio
async def test_health_postgres_up(client: AsyncClient):
    result = await client.get("/health")
    assert result.status_code == 200
    data = result.json()
    assert data["checks"]["postgres"] == "up"

#ASGITransport skips the lifespan
# app.state.redis does not exist for this test
#"down" is checking when the pool was never created
@pytest.mark.asyncio
async def test_health_redis_down_without_lifespan(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["checks"]["redis"] == "down"
    assert data["status"] == "degraded"

class FailingEngine:
    def connect(self):
        raise OSError("connection refused")

@pytest.mark.asyncio
async def test_health_postgres_down(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(main, "engine", FailingEngine())
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["checks"]["postgres"] == "down"
    assert data["status"] == "degraded"
