from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories import message_repo, user_repo
from app.schemas.message import MessageDetail, MessageListResponse, MessageRequest, MessageResponse
from app.services import message_processor
from app.services.message_service import MessageService

router = APIRouter(prefix="/api/v1/messages", tags=["messages"])

_svc = MessageService()


@router.post("", response_model=MessageResponse, status_code=201)
async def ingest_message(
    req: MessageRequest,
    x_user_id: int = Header(..., alias="X-tss-user-id"),
    db: AsyncSession = Depends(get_db),
):
    user = await user_repo.get_user_by_id(db, x_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    message_processor.process(req.content, user.user_id)

    result = await _svc.ingest(db, user_id=user.user_id, content=req.content)
    return MessageResponse(**result)


@router.get("/{message_id}", response_model=MessageDetail)
async def get_message(message_id: int, db: AsyncSession = Depends(get_db)):
    msg = await message_repo.get_message_by_id(db, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return MessageDetail(
        message_id=msg.message_id,
        content=msg.content,
        vibe_score=msg.vibe_score,
        received_at=msg.received_at,
    )


@router.get("", response_model=MessageListResponse)
async def list_messages(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    messages = await message_repo.list_all_messages(db, limit, offset)
    items = [
        MessageDetail(
            message_id=msg.message_id,
            content=msg.content,
            vibe_score=msg.vibe_score,
            received_at=msg.received_at,
        )
        for msg in messages
    ]
    return MessageListResponse(items=items, total=len(items), limit=limit, offset=offset)
