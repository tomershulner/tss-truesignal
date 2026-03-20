from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session, SessionMessage, SessionUser


async def create_session(db: AsyncSession) -> Session:
    session = Session()
    db.add(session)
    await db.flush()
    return session


async def get_session(db: AsyncSession, session_id: UUID) -> Session | None:
    result = await db.execute(select(Session).where(Session.session_id == session_id))
    return result.scalar_one_or_none()


async def get_session_user(
    db: AsyncSession, session_id: UUID, user_id: int
) -> SessionUser | None:
    result = await db.execute(
        select(SessionUser).where(
            SessionUser.session_id == session_id,
            SessionUser.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def add_session_message(
    db: AsyncSession, session_id: UUID, user_id: int, content: str
) -> SessionMessage:
    msg = SessionMessage(session_id=session_id, user_id=user_id, content=content)
    db.add(msg)
    await db.flush()
    return msg


async def list_session_messages(
    db: AsyncSession, session_id: UUID
) -> list[SessionMessage]:
    result = await db.execute(
        select(SessionMessage)
        .where(SessionMessage.session_id == session_id)
        .order_by(SessionMessage.sent_at.asc())
    )
    return list(result.scalars().all())


async def list_session_messages_since(
    db: AsyncSession, session_id: UUID, since_id: int
) -> list[SessionMessage]:
    result = await db.execute(
        select(SessionMessage)
        .where(SessionMessage.session_id == session_id, SessionMessage.id > since_id)
        .order_by(SessionMessage.id.asc())
    )
    return list(result.scalars().all())


async def add_session_users(
    db: AsyncSession, session_id: UUID, user_ids: list[int]
) -> None:
    if not user_ids:
        return
    rows = [{"session_id": session_id, "user_id": uid} for uid in user_ids]
    stmt = insert(SessionUser).values(rows).on_conflict_do_nothing()
    await db.execute(stmt)
    await db.flush()


async def delete_session_messages(db: AsyncSession, session_id: UUID) -> None:
    await db.execute(delete(SessionMessage).where(SessionMessage.session_id == session_id))
    await db.flush()


async def delete_session_users(db: AsyncSession, session_id: UUID) -> None:
    await db.execute(delete(SessionUser).where(SessionUser.session_id == session_id))
    await db.flush()
