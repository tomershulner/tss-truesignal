class VibeService:
    @staticmethod
    def compute_vibe_score(dimension_scores: list[float]) -> float:
        """Average of dimension scores (0.0–1.0), scaled to 0–100."""
        if not dimension_scores:
            return 0.0
        return round(sum(dimension_scores) / len(dimension_scores) * 100, 2)
