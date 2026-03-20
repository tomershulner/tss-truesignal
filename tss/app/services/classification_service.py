from app.classification.base import ClassificationResult
from app.classification.registry import get_classifier


class ClassificationService:
    def __init__(self):
        self._classifier = get_classifier()

    async def classify(self, content: str) -> ClassificationResult:
        return await self._classifier.classify(content)

    @staticmethod
    def to_integer_scores(
        result: ClassificationResult,
        score_type_map: dict[str, int],  # {name: score_type_id}
    ) -> dict[int, int]:
        """Map float 0.0–1.0 scores to integer 0–100, keyed by score_type_id."""
        return {
            score_type_map[name]: round(value * 100)
            for name, value in result.scores.items()
            if name in score_type_map
        }
