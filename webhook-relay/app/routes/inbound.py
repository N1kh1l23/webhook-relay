"""
Inbound Webhook Capture — YOU implement the handler logic.

Endpoint:
  POST /in/{source_token} — Receive a webhook, store the raw request, return 202
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.source import Source
from app.models.event import Event

router = APIRouter()


@router.post("/in/{source_token}", status_code=202)
async def receive_webhook(source_token: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    TODO — Implement this yourself:
    1. Look up the Source by its token
       - If no source found, return 404

    2. Capture the raw request data:
       - headers: dict(request.headers)
       - body: await request.json()  (wrap in try/except for non-JSON bodies)
       - query_params: dict(request.query_params)

    3. Create a new Event row with:
       - source_id from the looked-up source
       - the captured headers, body, query_params
       - status = "pending"

    4. Add to session, flush

    5. Return {"event_id": str(event.id), "status": "accepted"}

    HINTS:
    - Use `select(Source).where(Source.token == source_token)` to find the source
    - For non-JSON bodies, catch JSONDecodeError and store the raw text as {"raw": body_text}
    - request.headers is a special type — cast with dict() to make it JSON-serializable
    """
    raise NotImplementedError("Implement receive_webhook")
