import time
from dataclasses import dataclass, field

LOBBY_MAX_PLAYERS = 15
GAME_TRIGGER_THRESHOLD = 1
LOBBY_THRESHOLDS: dict[int, int] = {}
SESSION_DURATION_SECONDS = 300  # 5 minutes


CSGO_MAP_NAMES = {
    1: "Dust II",
    2: "Mirage",
    3: "Inferno",
    4: "Nuke",
    5: "Overpass",
    6: "Vertigo",
    7: "Ancient",
    8: "Anubis",
}


@dataclass
class LobbyState:
    lobby_id: int
    name: str = ""
    players: dict[int, str] = field(default_factory=dict)  # user_id -> display_name
    status: str = "waiting"  # "waiting" | "in_game"
    session_id: str | None = None
    started_at: float | None = None


_lobbies: dict[int, LobbyState] = {
    1: LobbyState(lobby_id=1, name=CSGO_MAP_NAMES.get(1, "Lobby 1"))
}


def get_all_lobbies() -> list[LobbyState]:
    return list(_lobbies.values())


def get_lobby(lobby_id: int) -> LobbyState | None:
    return _lobbies.get(lobby_id)


def join_lobby(lobby_id: int, user_id: int, display_name: str) -> LobbyState:
    lobby = _lobbies.get(lobby_id)
    if lobby is None:
        raise ValueError(f"Lobby {lobby_id} does not exist")
    if lobby.status != "waiting":
        raise ValueError(f"Lobby {lobby_id} is not accepting players (status={lobby.status})")
    if len(lobby.players) >= LOBBY_MAX_PLAYERS:
        raise ValueError(f"Lobby {lobby_id} is full")
    lobby.players[user_id] = display_name
    return lobby


def leave_lobby(lobby_id: int, user_id: int) -> None:
    lobby = _lobbies.get(lobby_id)
    if lobby is None:
        return
    lobby.players.pop(user_id, None)
    if len(lobby.players) == 0 and lobby.status == "in_game":
        lobby.status = "waiting"
        lobby.session_id = None
        lobby.started_at = None


def reset_lobby(lobby_id: int) -> None:
    lobby = _lobbies.get(lobby_id)
    if lobby is None:
        return
    lobby.players.clear()
    lobby.status = "waiting"
    lobby.session_id = None
    lobby.started_at = None


def reset_all_lobbies() -> None:
    for lobby_id, lobby in _lobbies.items():
        lobby.players.clear()
        lobby.status = "waiting"
        lobby.session_id = None
        lobby.started_at = None


def set_in_game(lobby_id: int, session_id: str) -> None:
    lobby = _lobbies.get(lobby_id)
    if lobby is None:
        return
    lobby.status = "in_game"
    lobby.session_id = session_id
    lobby.started_at = time.time()
