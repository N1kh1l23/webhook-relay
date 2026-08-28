"""
Shared test fixtures. This is boilerplate — study it so you understand
how the test database and client are set up, but this is config, not logic.
"""
import os
from collections.abc import AsyncGenerator
from types import SimpleNamespace

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import Base, get_db
from app.main import app
from app.queue import get_redis

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://webhook:webhook@localhost:5432/webhook_relay_test",
)


test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
test_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with test_session() as session:
        yield session

class FakeArqRedis:
    def __init__(self):
        self.enqueued = []

    async def enqueue_job(self, function_name, *args, **kwargs):
        self.enqueued.append((function_name, args, kwargs))
        return SimpleNamespace(job_id="fake-job-id")


@pytest_asyncio.fixture
async def fake_redis() -> FakeArqRedis:
    return FakeArqRedis()

@pytest_asyncio.fixture
async def client(db: AsyncSession, fake_redis) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client that talks to the FastAPI app with the test DB."""
    async def override_get_db():
        async with test_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = lambda: fake_redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
