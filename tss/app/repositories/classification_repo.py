from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.classification import Score, ScoreEntityType, ScoreType
from app.models.message import Message, MessageType


async def get_active_score_types(db: AsyncSession) -> list[ScoreType]:
    result = await db.execute(
        select(ScoreType).where(ScoreType.is_active == True)  # noqa: E712
    )
    return list(result.scalars().all())


async def bulk_upsert_scores(
    db: AsyncSession,
    entity_type: ScoreEntityType,
    entity_id: int,
    scores: dict[int, int],  # {score_type_id: score 0-100}
) -> list[Score]:
    """Insert or update one score row per (entity, score_type)."""
    if not scores:
        return []

    rows = [
        {
            "entity_type": entity_type.value,
            "entity_id": entity_id,
            "score_type_id": score_type_id,
            "score": score,
        }
        for score_type_id, score in scores.items()
    ]

    ins = insert(Score).values(rows)
    stmt = ins.on_conflict_do_update(
        constraint="uq_scores_entity_dim",
        set_={"score": ins.excluded.score},
    ).returning(Score)
    result = await db.execute(stmt)
    await db.flush()
    return list(result.scalars().all())


async def get_entity_scores(
    db: AsyncSession, entity_type: ScoreEntityType, entity_id: int
) -> list[Score]:
    result = await db.execute(
        select(Score)
        .where(Score.entity_type == entity_type, Score.entity_id == entity_id)
    )
    return list(result.scalars().all())


async def get_all_message_scores(
    db: AsyncSession, message_ids: list[int]
) -> dict[int, list[Score]]:
    """Batch fetch scores for multiple messages. Returns {message_id: [Score, ...]}."""
    if not message_ids:
        return {}
    result = await db.execute(
        select(Score).where(
            Score.entity_type == ScoreEntityType.message,
            Score.entity_id.in_(message_ids),
        )
    )
    out: dict[int, list[Score]] = {mid: [] for mid in message_ids}
    for s in result.scalars().all():
        out[s.entity_id].append(s)
    return out


async def get_all_user_scores(
    db: AsyncSession, user_ids: list[int]
) -> dict[int, list[Score]]:
    """Batch fetch scores for multiple users. Returns {user_id: [Score, ...]}."""
    if not user_ids:
        return {}
    result = await db.execute(
        select(Score).where(
            Score.entity_type == ScoreEntityType.user,
            Score.entity_id.in_(user_ids),
        )
    )
    out: dict[int, list[Score]] = {uid: [] for uid in user_ids}
    for s in result.scalars().all():
        out[s.entity_id].append(s)
    return out


async def get_avg_verbal_scores_for_user(
    db: AsyncSession, user_id: int
) -> dict[int, int]:
    """Average scores across all verbal messages for a user, keyed by score_type_id."""
    rows = await db.execute(
        select(Score.score_type_id, func.round(func.avg(Score.score)).label("avg_score"))
        .join(Message, (Score.entity_id == Message.message_id) & (Score.entity_type == ScoreEntityType.message))
        .where(Message.user_id == user_id, Message.message_type == MessageType.verbal)
        .group_by(Score.score_type_id)
    )
    return {row.score_type_id: int(row.avg_score) for row in rows}


async def get_verbal_score_contributions_for_user(
    db: AsyncSession, user_id: int
) -> dict[int, list[dict]]:
    """Per-message scores for all verbal messages of a user, grouped by score_type_id."""
    rows = await db.execute(
        select(Score.score_type_id, Score.entity_id.label("message_id"), Score.score, Message.received_at)
        .join(Message, (Score.entity_id == Message.message_id) & (Score.entity_type == ScoreEntityType.message))
        .where(Message.user_id == user_id, Message.message_type == MessageType.verbal)
        .order_by(Score.score_type_id, Message.received_at.desc())
    )
    result: dict[int, list[dict]] = {}
    for row in rows:
        result.setdefault(row.score_type_id, []).append(
            {"message_id": row.message_id, "score": row.score, "received_at": row.received_at}
        )
    return result
