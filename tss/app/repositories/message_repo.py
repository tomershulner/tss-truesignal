from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


async def insert_message(db: AsyncSession, content: str) -> Message:
    message = Message(content=content)
    db.add(message)
    await db.flush()
    return message


async def get_message_by_id(db: AsyncSession, message_id: int) -> Message | None:
    result = await db.execute(
        select(Message).where(Message.message_id == message_id)
    )
    return result.scalar_one_or_none()


async def list_all_messages(db: AsyncSession, limit: int = 20, offset: int = 0) -> list[Message]:
    result = await db.execute(
        select(Message).order_by(Message.received_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def update_message_vibe_score(
    db: AsyncSession, message_id: int, vibe_score: float
) -> None:
    await db.execute(
        text("UPDATE messages SET vibe_score = :score WHERE message_id = :id"),
        {"score": vibe_score, "id": message_id},
    )
    await db.flush()


async def get_message_by_content(db: AsyncSession, content: str) -> Message | None:
    result = await db.execute(select(Message).where(Message.content == content))
    return result.scalar_one_or_none()


async def upsert_message_vibe_score(db: AsyncSession, content: str, vibe_score: float) -> None:
    stmt = (
        insert(Message)
        .values(content=content, vibe_score=vibe_score)
        .on_conflict_do_update(
            index_elements=["content"],
            set_={"vibe_score": vibe_score},
        )
    )
    await db.execute(stmt)
    await db.flush()
