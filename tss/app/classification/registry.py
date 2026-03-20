from app.classification.base import BaseClassifier
from app.classification.stub import StubClassifier

# Swap StubClassifier for a real implementation here; no other code changes needed.
_classifier: BaseClassifier = StubClassifier()


def get_classifier() -> BaseClassifier:
    return _classifier
