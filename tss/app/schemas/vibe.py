from pydantic import BaseModel


class VibeScoreResponse(BaseModel):
    user_id: int
    vibe_score: float
    scores: dict[str, int]  # {dimension_name: 0-100}


class DimensionContribution(BaseModel):
    dimension: str
    score: int
    contributions: list[dict]


class UserScoreBreakdown(BaseModel):
    user_id: int
    vibe_score: float
    dimensions: list[DimensionContribution]


class MessageScoreBreakdown(BaseModel):
    message_id: int
    message_type: str
    dimensions: list[DimensionContribution]
