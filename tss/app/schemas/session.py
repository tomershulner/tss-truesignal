from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateSessionResponse(BaseModel):
    session_id: UUID
    created_at: datetime
    status: str


class AddUsersRequest(BaseModel):
    user_ids: list[int] = Field(..., max_length=100)


class AddUsersResponse(BaseModel):
    accepted: bool
    session_id: UUID
    user_count: int


class SessionMessageRequest(BaseModel):
    user_id: int
    content: str


class SessionMessageResponse(BaseModel):
    id: int
    vibe_score: float | None
