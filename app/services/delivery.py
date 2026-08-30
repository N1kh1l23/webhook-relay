import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.delivery_attempt import DeliveryAttempt
from app.models.event import Event
from app.services.retry_policy import Outcome, classify, next_delay, parse_retry_after


@dataclass(frozen=True)
class DeliveryResult:
    """
    What deliver_event decided, handed back to the caller.

    The worker reads this to schedule the retry. deliver_event itself never
    touches Redis — it writes the audit row and reports what should happen
    next, which keeps it testable with only a database.
    """

    outcome: Outcome
    attempt_number: int
    computed_delay_ms: int | None = None
    applied_delay_ms: int | None = None
    next_attempt_at: datetime | None = None

    @property
    def should_retry(self) -> bool:
        return self.applied_delay_ms is not None

async def deliver_event(
    db: AsyncSession,
    event_id: str,
    destination_url: str,
    previous_delay_ms: int | None = None,
) -> DeliveryResult:
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
        outcome_input = resp
        error_name = None
    except (httpx.RequestError, httpx.InvalidURL) as exc:
        status = None
        response_text = None
        outcome_input = exc
        error_name = type(exc).__name__

    duration_ms = int((time.perf_counter() - start) * 1000)

    outcome = classify(outcome_input)

    computed_delay_ms = None
    applied_delay_ms = None
    next_attempt_at = None

    if outcome is Outcome.SUCCESS:
        event_status = "delivered"
    elif outcome is Outcome.TERMINAL:
        event_status = "dead_lettered"
    elif attempt_number >= settings.max_delivery_attempts:
        event_status = "dead_lettered"
    else:
        event_status = "retrying"
        computed_delay_ms = next_delay(
            previous_delay_ms or 0,
            base_ms=settings.retry_base_ms,
            cap_ms=settings.retry_cap_ms,
        )
        retry_after_ms = parse_retry_after(resp) if status is not None else None
        applied_delay_ms = retry_after_ms if retry_after_ms is not None else computed_delay_ms
        next_attempt_at = datetime.now(timezone.utc) + timedelta(milliseconds=applied_delay_ms)

    truncated_text = response_text[:1000] if response_text is not None else None
    new_delivery_attempt = DeliveryAttempt(
        event_id=event.id,
        destination_url=destination_url,
        response_status=status,
        response_body=truncated_text,
        duration_ms=duration_ms,
        attempt_number=attempt_number,
        outcome=outcome.value,
        error_type=error_name,
        computed_delay_ms=computed_delay_ms,
        applied_delay_ms=applied_delay_ms,
        next_attempt_at=next_attempt_at,
    )
    db.add(new_delivery_attempt)
    await db.flush()

    event.status = event_status
    await db.commit()


    return DeliveryResult(
        outcome=outcome,
        attempt_number=attempt_number,
        computed_delay_ms=computed_delay_ms,
        applied_delay_ms=applied_delay_ms,
        next_attempt_at=next_attempt_at,
    )
