from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ClassificationResult:
    """Scores per dimension, float 0.0–1.0."""
    scores: dict[str, float]  # {score_type_name: 0.0–1.0}
    raw: dict  # raw classifier output for storage


class BaseClassifier(ABC):
    @abstractmethod
    async def classify(self, content: str) -> ClassificationResult:
        """Classify text content and return per-dimension scores."""
