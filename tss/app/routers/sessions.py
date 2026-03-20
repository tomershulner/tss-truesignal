from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.repositories import message_repo, session_repo, user_repo
from app.services.message_processor import is_nonverbal
from app.schemas.session import (
    AddUsersRequest,
    AddUsersResponse,
    CreateSessionResponse,
    SessionMessageRequest,
    SessionMessageResponse,
)

router = APIRouter(tags=["sessions"])


@router.post("/session/create", response_model=CreateSessionResponse, status_code=201)
async def create_session(db: AsyncSession = Depends(get_db)):
    session = await session_repo.create_session(db)
    await db.commit()
    return CreateSessionResponse(
        session_id=session.session_id,
        created_at=session.created_at,
        status=session.status,
    )


@router.post("/{session_id}/users", response_model=AddUsersResponse, status_code=202)
async def add_users_to_session(
    session_id: UUID,
    body: AddUsersRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    if len(body.user_ids) > 100:
        raise HTTPException(status_code=422, detail="Cannot register more than 100 users per request")

    session = await session_repo.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    background_tasks.add_task(_add_users, session_id, body.user_ids)

    return AddUsersResponse(
        accepted=True,
        session_id=session_id,
        user_count=len(body.user_ids),
    )


async def _add_users(session_id: UUID, user_ids: list[int]) -> None:
    async with AsyncSessionLocal() as db:
        await session_repo.add_session_users(db, session_id, user_ids)
        await db.commit()


@router.post("/{session_id}/message", response_model=SessionMessageResponse)
async def session_message(
    session_id: UUID,
    body: SessionMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    session = await session_repo.get_session(db, session_id)
    if not session or session.status != "active":
        raise HTTPException(status_code=404, detail="Session not found or not active")

    session_user = await session_repo.get_session_user(db, session_id, body.user_id)
    if not session_user:
        raise HTTPException(status_code=404, detail="User not found in session")

    msg = await session_repo.add_session_message(db, session_id, body.user_id, body.content)
    existing = await message_repo.get_message_by_content(db, body.content)
    await db.commit()

    return SessionMessageResponse(id=msg.id, vibe_score=existing.vibe_score if existing else None)


@router.post("/{session_id}/close", status_code=200)
async def close_session(
    session_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    session = await session_repo.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.status = "closed"
    await db.commit()

    background_tasks.add_task(_process_session_close, session_id)

    return {"session_id": session_id}


class SessionMessageOut(BaseModel):
    id: int
    user_id: int
    content: str


@router.get("/{session_id}/check-message")
async def check_message_vibe(
    session_id: UUID,
    content: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    existing = await message_repo.get_message_by_content(db, content)
    return {"vibe_score": existing.vibe_score if existing else None}


@router.get("/{session_id}/messages", response_model=list[SessionMessageOut])
async def list_messages_since(
    session_id: UUID,
    since_id: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    messages = await session_repo.list_session_messages_since(db, session_id, since_id)
    return [SessionMessageOut(id=m.id, user_id=m.user_id, content=m.content) for m in messages]


async def _process_session_close(session_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        messages = await session_repo.list_session_messages(db, session_id)
        if not messages:
            await session_repo.delete_session_users(db, session_id)
            await db.commit()
            return

        content_to_users: dict[str, list[int]] = {}
        for msg in messages:
            content_to_users.setdefault(msg.content, []).append(msg.user_id)

        for content, user_ids in content_to_users.items():
            if not is_nonverbal(content):
                continue
            scores = await user_repo.get_user_vibe_scores(db, list(set(user_ids)))
            if not scores:
                continue
            new_score = sum(scores.values()) / len(scores)
            existing = await message_repo.get_message_by_content(db, content)
            if existing:
                if new_score < existing.vibe_score:
                    continue
                final_score = round((existing.vibe_score + new_score) / 2, 2)
            else:
                final_score = round(new_score, 2)
            await message_repo.upsert_message_vibe_score(db, content, final_score)

        await session_repo.delete_session_messages(db, session_id)
        await session_repo.delete_session_users(db, session_id)
        await db.commit()
