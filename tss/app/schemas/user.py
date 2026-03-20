from datetime import datetime

from pydantic import BaseModel


class UserResponse(BaseModel):
    user_id: int
    external_id: str | None
    created_at: datetime
    updated_at: datetime


class UserWithScoreResponse(BaseModel):
    user_id: int
    external_id: str | None
    created_at: datetime
    updated_at: datetime
    vibe_score: float
    scores: dict[str, int]


class UserListResponse(BaseModel):
    users: list[UserWithScoreResponse]
    total: int


class BulkCreateUsersRequest(BaseModel):
    count: int
    display_names: list[str] | None = None


class BulkCreateUsersResponse(BaseModel):
    users: list[UserResponse]
    total: int
    created: int
