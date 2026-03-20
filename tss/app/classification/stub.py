import random

from app.classification.base import BaseClassifier, ClassificationResult

DIMENSIONS = ["harmful", "hate", "sexual_harassment"]


class StubClassifier(BaseClassifier):
    """Development stub: returns random scores (seeded for reproducibility in tests)."""

    async def classify(self, content: str) -> ClassificationResult:
        scores = {dim: round(random.uniform(0.0, 1.0), 4) for dim in DIMENSIONS}
        return ClassificationResult(scores=scores, raw={"stub": True, "scores": scores})
