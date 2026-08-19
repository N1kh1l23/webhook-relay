"""
Replay — YOU implement the handler logic.

Endpoints:
  POST /events/{event_id}/replay   — send a stored event to a destination
  GET  /events/{event_id}/attempts — delivery history
"""
import time

import httpx
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

    