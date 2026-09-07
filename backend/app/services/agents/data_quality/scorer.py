from typing import List, Dict, Any, Tuple
from backend.app.models.domain import DataQualityRuleViolation

class DataQualityScorer:
    """
    Deterministic scoring model that maps rule violations and penalties to
    a 0-100 quality score and categorical classification.
    """

    REJECTION_THRESHOLD = 50.0
    WARNING_THRESHOLD = 70.0
    VALID_THRESHOLD = 90.0

    @classmethod
    def calculate_score(
        cls,
        issues: List[DataQualityRuleViolation],
        warnings: List[DataQualityRuleViolation],
        field_scores: Dict[str, float]
    ) -> Tuple[float, str, bool]:
        """
        Calculates score (0.0 - 100.0), classification, and trusted flag.
        Returns:
            overall_score: float
            classification: "valid" | "valid_with_warnings" | "needs_review" | "rejected"
            is_trusted: bool (False only if rejected)
        """
        score = 100.0

        # Critical issue penalties
        for iss in issues:
            score -= iss.penalty_score

        # Warning penalties
        for warn in warnings:
            score -= warn.penalty_score

        # Clamp score to [0.0, 100.0]
        score = max(0.0, min(100.0, score))
        score = round(score, 1)

        # Determine Classification
        if issues and score < cls.REJECTION_THRESHOLD:
            classification = "rejected"
            is_trusted = False
        elif score < cls.REJECTION_THRESHOLD:
            classification = "rejected"
            is_trusted = False
        elif score < cls.WARNING_THRESHOLD:
            classification = "needs_review"
            is_trusted = True
        elif score < cls.VALID_THRESHOLD:
            classification = "valid_with_warnings"
            is_trusted = True
        else:
            classification = "valid"
            is_trusted = True

        return score, classification, is_trusted
