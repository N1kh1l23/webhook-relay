import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id"), index=True
    )
    destination_url: Mapped[str] = mapped_column(Text)
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int] = mapped_column(Integer)
    attempt_number: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(20))
    error_type: Mapped[str | None] = mapped_column(String(100))
    computed_delay_ms: Mapped[int | None] = mapped_column(Integer)
    applied_delay_ms: Mapped[int | None] = mapped_column(Integer)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
