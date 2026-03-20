import asyncio
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.repositories import session_repo
from app.services import lobby_service
from app.services.lobby_service import GAME_TRIGGER_THRESHOLD, LOBBY_THRESHOLDS, SESSION_DURATION_SECONDS

router = APIRouter(prefix="/api/v1/lobbies", tags=["lobbies"])


class LobbyPlayerInfo(BaseModel):
    user_id: int
    display_name: str


class LobbyResponse(BaseModel):
    lobby_id: int
    name: str
    player_count: int
    players: list[LobbyPlayerInfo]
    status: str
    session_id: str | None


class JoinLobbyRequest(BaseModel):
    user_id: int
    display_name: str


class JoinLobbyResponse(BaseModel):
    lobby_id: int
    player_count: int
    status: str
    session_id: str | None


class LeaveRequest(BaseModel):
    user_id: int


def _to_response(lobby: lobby_service.LobbyState) -> LobbyResponse:
    return LobbyResponse(
        lobby_id=lobby.lobby_id,
        name=lobby.name,
        player_count=len(lobby.players),
        players=[LobbyPlayerInfo(user_id=uid, display_name=name) for uid, name in lobby.players.items()],
        status=lobby.status,
        session_id=lobby.session_id,
    )


@router.get("", response_model=list[LobbyResponse])
async def list_lobbies():
    return [_to_response(l) for l in lobby_service.get_all_lobbies()]


@router.get("/{lobby_id}", response_model=LobbyResponse)
async def get_lobby(lobby_id: int):
    lobby = lobby_service.get_lobby(lobby_id)
    if lobby is None:
        raise HTTPException(status_code=404, detail="Lobby not found")
    return _to_response(lobby)


async def _auto_close_session(lobby_id: int, session_id: UUID) -> None:
    await asyncio.sleep(SESSION_DURATION_SECONDS)
    async with AsyncSessionLocal() as db:
        session = await session_repo.get_session(db, session_id)
        if session and session.status == "active":
            session.status = "closed"
            await db.commit()
    lobby_service.reset_lobby(lobby_id)


@router.post("/{lobby_id}/join", response_model=JoinLobbyResponse)
async def join_lobby(
    lobby_id: int,
    body: JoinLobbyRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    try:
        lobby = lobby_service.join_lobby(lobby_id, body.user_id, body.display_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Trigger game if threshold reached
    threshold = LOBBY_THRESHOLDS.get(lobby_id, GAME_TRIGGER_THRESHOLD)
    if len(lobby.players) >= threshold and lobby.status == "waiting":
        session = await session_repo.create_session(db)
        await db.flush()
        await session_repo.add_session_users(db, session.session_id, list(lobby.players.keys()))
        await db.commit()
        lobby_service.set_in_game(lobby_id, str(session.session_id))
        background_tasks.add_task(_auto_close_session, lobby_id, session.session_id)

    return JoinLobbyResponse(
        lobby_id=lobby.lobby_id,
        player_count=len(lobby.players),
        status=lobby.status,
        session_id=lobby.session_id,
    )


@router.post("/{lobby_id}/leave")
async def leave_lobby(lobby_id: int, body: LeaveRequest):
    lobby_service.leave_lobby(lobby_id, body.user_id)
    return {"ok": True}


@router.post("/reset")
async def reset_all_lobbies():
    lobby_service.reset_all_lobbies()
    return {"ok": True}
