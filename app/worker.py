from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401  # registers all mappers for this process
from app.config import settings
from app.services.delivery import deliver_event


async def startup(ctx):
    engine = create_async_engine(settings.database_url, echo=False)
    ctx["engine"] = engine
    ctx["session_factory"] = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )


async def shutdown(ctx):
    await ctx["engine"].dispose()

async def queued_replay_job(ctx, event_id: str, destination_url: str) -> None:
    async with ctx["session_factory"]() as session:
        await deliver_event(session, event_id, destination_url)

class WorkerSettings:
    functions = [queued_replay_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    # arq polls Redis for due jobs with a zrangebyscore per iteration; Upstash
    # bills per command. 5s costs ~$1/month against ~$10 at the 0.5s default.
    # This is a floor on retry precision: a job deferred by N seconds fires
    # somewhere in [N, N+5]. Base backoff is 15s to keep the slop under a third.
    poll_delay = 5
    on_startup = startup
    on_shutdown = shutdown
