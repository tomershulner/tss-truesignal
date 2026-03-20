from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def create_user(db: AsyncSession, external_id: str | None = None) -> User:
    user = User(external_id=external_id)
    db.add(user)
    await db.flush()
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_external_id(db: AsyncSession, external_id: str) -> User | None:
    result = await db.execute(select(User).where(User.external_id == external_id))
    return result.scalar_one_or_none()


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


async def get_user_vibe_scores(db: AsyncSession, user_ids: list[int]) -> dict[int, float]:
    if not user_ids:
        return {}
    result = await db.execute(
        select(User.user_id, User.vibe_score).where(User.user_id.in_(user_ids))
    )
    return {row.user_id: row.vibe_score for row in result.fetchall()}


async def update_user_vibe_score(db: AsyncSession, user_id: int, vibe_score: float) -> None:
    await db.execute(
        text("UPDATE users SET vibe_score = :score WHERE user_id = :id"),
        {"score": vibe_score, "id": user_id},
    )
    await db.flush()


async def bulk_create_users(
    db: AsyncSession, count: int, external_ids: list[str | None] | None = None
) -> list[User]:
    users = [
        User(external_id=external_ids[i] if external_ids and i < len(external_ids) else None)
        for i in range(count)
    ]
    db.add_all(users)
    await db.flush()
    return users
