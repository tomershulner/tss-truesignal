from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories import user_repo
from app.schemas.user import (
    BulkCreateUsersRequest,
    BulkCreateUsersResponse,
    UserListResponse,
    UserResponse,
    UserWithScoreResponse,
)
from app.schemas.vibe import VibeScoreResponse
from app.services import session_cache

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(db: AsyncSession = Depends(get_db)):
    users = await user_repo.list_users(db)
    result = [
        UserWithScoreResponse(
            user_id=u.user_id,
            external_id=u.external_id,
            created_at=u.created_at,
            updated_at=u.updated_at,
            vibe_score=u.vibe_score,
            scores={},
        )
        for u in users
    ]
    return UserListResponse(users=result, total=len(result))


@router.post("/bulk", response_model=BulkCreateUsersResponse)
async def bulk_create_users(body: BulkCreateUsersRequest, db: AsyncSession = Depends(get_db)):
    users = await user_repo.bulk_create_users(db, body.count, body.display_names)
    await db.commit()

    session_cache.initialize({u.user_id: u.vibe_score for u in users})

    return BulkCreateUsersResponse(
        users=[UserResponse.model_validate(u, from_attributes=True) for u in users],
        total=len(users),
        created=len(users),
    )


@router.get("/by-username/{external_id}", response_model=UserResponse)
async def get_user_by_external_id(external_id: str, db: AsyncSession = Depends(get_db)):
    user = await user_repo.get_user_by_external_id(db, external_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user, from_attributes=True)


@router.get("/{user_id}/vibe-score", response_model=VibeScoreResponse)
async def get_vibe_score(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await user_repo.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return VibeScoreResponse(
        user_id=user.user_id,
        vibe_score=user.vibe_score,
        scores={},
    )
