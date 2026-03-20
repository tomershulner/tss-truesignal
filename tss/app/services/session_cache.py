"""
In-memory session cache.
Populated once per session via POST /api/v1/users/bulk.
Maps user_id → vibe score so the message processor can access it without a DB round-trip.
"""

_scores: dict[int, float] = {}


def initialize(scores: dict[int, float]) -> None:
    """Replace the entire cache. Called at session start."""
    _scores.clear()
    _scores.update(scores)


def set_score(user_id: int, score: float) -> None:
    _scores[user_id] = score


def get_score(user_id: int) -> float | None:
    return _scores.get(user_id)
