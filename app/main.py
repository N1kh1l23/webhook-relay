from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, Request
from sqlalchemy import text

from app.config import settings
from app.database import engine
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
async def health(request: Request):

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        postgres = "up"
    except Exception:
        postgres = "down"

    pool = getattr(request.app.state, "redis", None)

    if pool is None:
        redis = "down"
    else:
        try:
            await pool.ping()
            redis = "up"
        except Exception:
            redis = "down"

    if postgres == "up" and redis == "up":
        status = "ok"
    else:
        status = "degraded"

    checks = {"postgres": postgres, "redis": redis}
    response = {"status": status, "checks": checks}
    return response
