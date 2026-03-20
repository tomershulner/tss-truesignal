from datetime import datetime

from sqlalchemy import BigInteger, Double, Identity, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_received_at", "received_at"),
        UniqueConstraint("content", name="uq_messages_content"),
    )

    message_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    vibe_score: Mapped[float] = mapped_column(Double, nullable=False, server_default="0.0")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
