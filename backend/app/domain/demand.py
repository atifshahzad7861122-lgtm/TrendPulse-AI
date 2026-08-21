from typing import Tuple, List, Dict, Any

class DemandEvaluationResult:
    def __init__(
        self,
        label: str,
        demand_score: float,
        confidence: int,
        contributors: List[str],
        engine_version: str = "2.4.0"
    ):
        self.label = label
        self.demand_score = demand_score
        self.confidence = confidence
        self.contributors = contributors
        self.engine_version = engine_version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "demand_score": self.demand_score,
            "confidence": self.confidence,
            "contributors": self.contributors,
            "engine_version": self.engine_version
        }

class DemandSignalEngine:
    """
    Evaluates underlying engagement, volume, and sentiment signals
    to calculate commercial product demand strength and confidence.
    """

    ENGINE_VERSION = "2.4.0"

    @staticmethod
    def evaluate_demand_detailed(
        volume: int,
        sentiment_score: float,
        growth_rate: float,
        engagement_rate: float = 0.08
    ) -> DemandEvaluationResult:
        """
        Derives demand label, numeric conviction index (0-100), confidence percentage,
        and specific explainable contributors.
        """
        vol_factor = min(volume / 200000.0, 1.0) * 40.0
        sentiment_factor = min(sentiment_score, 1.0) * 35.0
        growth_factor = min(growth_rate / 300.0, 1.0) * 25.0

        raw_index = vol_factor + sentiment_factor + growth_factor
        demand_index = round(min(max(raw_index, 10.0), 99.0), 1)

        # Classify label
        if demand_index >= 85.0:
            label = "Very Strong"
        elif demand_index >= 70.0:
            label = "Strong"
        elif demand_index >= 50.0:
            label = "Moderate"
        else:
            label = "Low"

        # Calculate confidence based on sentiment stability and volume depth
        confidence = int(min(60 + (sentiment_score * 25) + (min(volume / 100000.0, 1.0) * 15), 95))

        # Explainable contributors
        contributors = []
        if volume >= 150000:
            contributors.append("High marketplace search and view depth")
        if sentiment_score >= 0.88:
            contributors.append("Strong organic consumer sentiment")
        if growth_rate >= 150.0:
            contributors.append(f"Accelerating order interest (+{growth_rate:.0f}%)")
        if engagement_rate >= 0.07:
            contributors.append("Active audience comment & share engagement")
        if not contributors:
            contributors.append("Baseline organic search activity")

        return DemandEvaluationResult(
            label=label,
            demand_score=demand_index,
            confidence=confidence,
            contributors=contributors[:3],
            engine_version=DemandSignalEngine.ENGINE_VERSION
        )

    @staticmethod
    def evaluate_demand(
        volume: int,
        sentiment_score: float,
        growth_rate: float
    ) -> Tuple[str, float]:
        """Backward-compatible tuple return."""
        res = DemandSignalEngine.evaluate_demand_detailed(volume, sentiment_score, growth_rate)
        return res.label, res.demand_score
