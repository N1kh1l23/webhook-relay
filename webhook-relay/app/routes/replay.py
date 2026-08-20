"""
Replay — YOU implement the handler logic.

Endpoints:
  POST /events/{event_id}/replay   — send a stored event to a destination
  GET  /events/{event_id}/attempts — delivery history
"""
import time

import httpx
import uuid
from datetime import datetime
from httpx import AsyncClient
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.delivery_attempt import DeliveryAttempt
from app.models.event import Event


router = APIRouter()


class ReplayRequest(BaseModel):
    destination_url: str

class AttemptResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    destination_url: str
    response_status: int | None
    response_body: str | None
    duration_ms: int
    attempt_number: int
    attempted_at: datetime

    model_config = {"from_attributes": True}

@router.post("/events/{event_id}/replay")
async def replay_event(
    event_id: str,
    payload: ReplayRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    TODO — Implement this yourself:

    1. Look up the Event by id; 404 with a detail if missing.

    2. Work out attempt_number — count existing DeliveryAttempt rows for this
       event and add one. (You left the column with no default, so you must set it.)

    3. Start a timer before the request. time.perf_counter() is the right tool.

    4. Send it, with a 5s timeout per ARCHITECTURE.md:
           async with httpx.AsyncClient(timeout=5.0) as ac:
               resp = await ac.post(payload.destination_url, json=event.body)
       On success you have resp.status_code and resp.text.
       Wrap in try/except — httpx raises when no response arrives at all.
       Catch httpx.RequestError (TimeoutException is a subclass of it).

    5. Compute duration_ms in both paths — success AND failure.

    6. Decide the event's new status: "delivered" if the destination answered
       2xx, otherwise "failed".

    7. Create the DeliveryAttempt row, db.add(), await db.flush().
       Truncate response_body to the first 1000 chars per the spec.

    8. Set event.status.

    9. Return keys matching what your test asserts: "status" and "response_status".
    """
    event_check = await db.execute(select(Event).where(Event.id == event_id))
    event = event_check.scalar_one_or_none()
    if event is None:
        raise HTTPException(404, detail = "ID was not found")
    attempt_number_check = await db.execute(select(func.count()).where(DeliveryAttempt.event_id == event_id))
    attempt_number = attempt_number_check.scalar_one() + 1
    start = time.perf_counter()

    try:
        async with AsyncClient(timeout=5.0) as ac:
            resp = await ac.post(payload.destination_url, json=event.body)
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
    newDeliveryAttempt = DeliveryAttempt(event_id = event.id, destination_url = payload.destination_url, response_status = status, response_body = truncated_text, duration_ms = duration_ms, attempt_number = attempt_number)
    db.add(newDeliveryAttempt)
    await db.flush()

    event.status = event_status

    return {"status": event_status,"response_status": status}

@router.get("/events/{event_id}/attempts")
async def list_attempts(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    event_check = await db.execute(select(Event).where(Event.id == event_id))
    event = event_check.scalar_one_or_none()
    if event is None:
        raise HTTPException(404, detail = "ID was not found")
    
    attempts_result = await db.execute(select(DeliveryAttempt).where(DeliveryAttempt.event_id == event_id).order_by(DeliveryAttempt.attempt_number))
    attempts = attempts_result.scalars().all()
    attempt_responses = [AttemptResponse.model_validate(a) for a in attempts]
    return attempt_responses
    
    
