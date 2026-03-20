from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, ForeignKey, Identity, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID as pg_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[pg_UUID] = mapped_column(
        pg_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="active"
    )


class SessionUser(Base):
    __tablename__ = "session_users"

    session_id: Mapped[pg_UUID] = mapped_column(
        pg_UUID(as_uuid=True),
        ForeignKey("sessions.session_id"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id"), primary_key=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class SessionMessage(Base):
    __tablename__ = "session_messages"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    session_id: Mapped[pg_UUID] = mapped_column(
        pg_UUID(as_uuid=True),
        ForeignKey("sessions.session_id"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
