import time

import httpx
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery_attempt import DeliveryAttempt
from app.models.event import Event


async def deliver_event(db: AsyncSession, event_id: str, destination_url: str) -> None:
    event_check = await db.execute(select(Event).where(Event.id == event_id))
    event = event_check.scalar_one_or_none()
    if event is None:
        raise ValueError(f"{event_id} does not match a row")
    attempt_number_check = await db.execute(
        select(func.count()).where(DeliveryAttempt.event_id == event_id)
    )
    attempt_number = attempt_number_check.scalar_one() + 1

    start = time.perf_counter()

    try:
        async with AsyncClient(timeout=5.0) as ac:
            resp = await ac.post(destination_url, json=event.body)
        status = resp.status_code
        response_text = resp.text
    except httpx.RequestError:
        status = None
        response_text = None

    duration_ms = int((time.perf_counter() - start) * 1000)

    if (status is not None) and (199 < status < 300):
        event_status =  "delivered"
    else:
        event_status =  "failed"

    truncated_text = response_text[:1000] if response_text is not None else None
    new_delivery_attempt = DeliveryAttempt(
        event_id=event.id,
        destination_url=destination_url,
        response_status=status,
        response_body=truncated_text,
        duration_ms=duration_ms,
        attempt_number=attempt_number,
    )
    db.add(new_delivery_attempt)
    await db.flush()

    event.status = event_status
    await db.commit()
