from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.services.delivery import deliver_event
import app.models

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
    on_startup = startup
    on_shutdown = shutdown
