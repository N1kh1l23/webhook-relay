"""
Replay — YOU implement the handler logic.

Endpoints:
  POST /events/{event_id}/replay   — send a stored event to a destination
  GET  /events/{event_id}/attempts — delivery history
"""

import uuid
from datetime import datetime

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.delivery_attempt import DeliveryAttempt
from app.models.event import Event
from app.queue import get_redis

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

@router.post("/events/{event_id}/replay", status_code = 202)
async def replay_event(
    event_id: str,
    payload: ReplayRequest,
    db: AsyncSession = Depends(get_db),
    redis: ArqRedis = Depends(get_redis)
):
    """
     Queue a stored event for delivery to a destination URL.

    Confirms the event exists, then enqueues a job and returns 202. The
    outbound request runs in the arq worker, not in this request, so no
    delivery outcome is known here — poll GET /events/{event_id}/attempts.
    """
    event_check = await db.execute(select(Event).where(Event.id == event_id))
    event = event_check.scalar_one_or_none()
    if event is None:
        raise HTTPException(404, detail = "ID was not found")
    job = await redis.enqueue_job("queued_replay_job", event_id, payload.destination_url)
    return {"job_id": job.job_id, "event_id": event_id}

@router.get("/events/{event_id}/attempts")
async def list_attempts(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    event_check = await db.execute(select(Event).where(Event.id == event_id))
    event = event_check.scalar_one_or_none()
    if event is None:
        raise HTTPException(404, detail = "ID was not found")

    attempts_result = await db.execute(
        select(DeliveryAttempt)
        .where(DeliveryAttempt.event_id == event_id)
        .order_by(DeliveryAttempt.attempt_number)
    )
    attempts = attempts_result.scalars().all()
    attempt_responses = [AttemptResponse.model_validate(a) for a in attempts]
    return attempt_responses


