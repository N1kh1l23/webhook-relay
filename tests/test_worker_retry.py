import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.delivery_attempt import DeliveryAttempt
from app.models.event import Event
from app.services import delivery
from app.worker import queued_replay_job
from tests.fakes import ClientReplacement, ClientReplacementFail


class SessionFactory:
    """
    Hands the worker the test's existing session instead of opening a new one.

    queued_replay_job does `async with ctx["session_factory"]() as session`,
    so the factory must be callable and its return value must be an async
    context manager. __aexit__ deliberately does not close: the test still
    needs the session afterwards to read rows back.
    """

    def __init__(self, session):
        self.session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        pass


def make_ctx(session, redis):
    return {"session_factory": SessionFactory(session), "redis": redis}


@pytest.mark.asyncio
async def test_worker_schedules_retry_on_500(db, client: AsyncClient, monkeypatch, fake_redis):
    source_response = await client.post("/sources", json={"name": "replay-test"})
    source_data = source_response.json()
    new_token = source_data["token"]

    event_response = await client.post(f"/in/{new_token}", json={"event": "test"})
    event_data = event_response.json()
    event_id = event_data["event_id"]

    monkeypatch.setattr(delivery, "AsyncClient", ClientReplacementFail)

    ctx = make_ctx(db, fake_redis)
    await queued_replay_job(ctx, event_id, "https://hi.com/yo")

    assert len(fake_redis.enqueued) == 1

    function_name, args, kwargs = fake_redis.enqueued[0]
    assert function_name == "queued_replay_job"
    assert args[0] == event_id
    assert args[1] == "https://hi.com/yo"
    assert args[2] is not None
    assert "_defer_by" in kwargs


@pytest.mark.asyncio
async def test_worker_no_retry_on_success(db, client: AsyncClient, monkeypatch, fake_redis):
    source_response = await client.post("/sources", json={"name": "replay-test"})
    source_data = source_response.json()
    new_token = source_data["token"]

    event_response = await client.post(f"/in/{new_token}", json={"event": "test"})
    event_data = event_response.json()
    event_id = event_data["event_id"]

    monkeypatch.setattr(delivery, "AsyncClient", ClientReplacement)

    ctx = make_ctx(db, fake_redis)
    await queued_replay_job(ctx, event_id, "https://hi.com/yo")

    assert len(fake_redis.enqueued) == 0

@pytest.mark.asyncio
async def test_worker_dead_letters_after_max_attempts(
    db, client: AsyncClient, monkeypatch, fake_redis
):
    source_response = await client.post("/sources", json={"name": "replay-test"})
    source_data = source_response.json()
    new_token = source_data["token"]

    event_response = await client.post(f"/in/{new_token}", json={"event": "test"})
    event_data = event_response.json()
    event_id = event_data["event_id"]
    monkeypatch.setattr(delivery, "AsyncClient", ClientReplacementFail)
    ctx = make_ctx(db, fake_redis)

    previous_delay_ms = None
    for x in range(6):
        await queued_replay_job(ctx, event_id, "https://hi.com/yo", previous_delay_ms)
        if fake_redis.enqueued:
            previous_delay_ms = fake_redis.enqueued[-1][1][2]

    query = (
        select(DeliveryAttempt)
        .where(DeliveryAttempt.event_id == event_id)
        .order_by(DeliveryAttempt.attempt_number)
    )
    attempts_result = await db.execute(query)
    attempts = list(attempts_result.scalars().all())

    assert len(attempts) == 6
    assert len(fake_redis.enqueued) == 5
    event_result_check = await db.execute(select(Event).where(Event.id == event_id))
    event_result = event_result_check.scalar_one_or_none()
    assert event_result.status == "dead_lettered"

    assert attempts[5].outcome == "retry"
    assert attempts[5].next_attempt_at is None
    assert attempts[5].computed_delay_ms is None
    assert attempts[0].computed_delay_ms is not None
