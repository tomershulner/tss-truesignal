from datetime import datetime

from pydantic import BaseModel


class MessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    message_id: int
    user_id: int
    vibe_score: float


class MessageDetail(BaseModel):
    message_id: int
    content: str
    vibe_score: float
    received_at: datetime


class MessageListResponse(BaseModel):
    items: list[MessageDetail]
    total: int
    limit: int
    offset: int
