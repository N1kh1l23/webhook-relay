from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI

from app.config import settings
from app.routes import inbound, replay, sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    yield
    await app.state.redis.aclose()


app = FastAPI(
    title="Webhook Relay",
    description="Capture, inspect, and replay webhooks",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(replay.router, tags=["replay"])
app.include_router(sources.router, prefix="/sources", tags=["sources"])
app.include_router(inbound.router, tags=["inbound"])


@app.get("/health")
async def health():
    return {"status": "ok"}
