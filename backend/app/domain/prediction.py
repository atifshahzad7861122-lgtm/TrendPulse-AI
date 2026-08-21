from typing import List, Dict, Any, Optional
from backend.app.models.domain import Product
from backend.app.domain.scoring import TrendScoringEngine

class PredictionResult:
    def __init__(
        self,
        product_id: str,
        current_score: float,
        direction: str,  # "rising", "stable", "declining"
        confidence: int,  # 0 - 100
        predicted_score_7d: Optional[float],
        predicted_score_30d: Optional[float],
        prediction_status: str = "ready",  # "ready" | "insufficient_history"
        horizon_days: int = 30,
        methodology: str = "Exponential Velocity Momentum Smoothing",
        prediction_version: str = "2.4.0"
    ):
        self.product_id = product_id
        self.current_score = current_score
        self.direction = direction
        self.confidence = confidence
        self.predicted_score_7d = predicted_score_7d
        self.predicted_score_30d = predicted_score_30d
        self.prediction_status = prediction_status
        self.horizon_days = horizon_days
        self.methodology = methodology
        self.prediction_version = prediction_version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "current_score": self.current_score,
            "direction": self.direction,
            "confidence": self.confidence,
            "predicted_score_7d": self.predicted_score_7d,
            "predicted_score_30d": self.predicted_score_30d,
            "prediction_status": self.prediction_status,
            "horizon_days": self.horizon_days,
            "methodology": self.methodology,
            "prediction_version": self.prediction_version
        }

class TrendPredictionService:
    """
    Intelligence Agent: Generates deterministic statistical trajectory forecasts.
    Enforces strict historical data sufficiency gates to prevent fabricating projected scores.
    """

    PREDICTION_VERSION = "2.4.0"
    MIN_OBSERVATIONS_REQUIRED = 3

    @staticmethod
    def predict_product_trajectory(product: Product) -> PredictionResult:
        hist_scores = [h.get("score", 50.0) for h in product.historical_scores] if product.historical_scores else []
        current = product.trend_score
        growth = product.growth_rate

        # Historical sufficiency gate: If fewer than 3 observations, do not fabricate projected numbers
        if len(hist_scores) < TrendPredictionService.MIN_OBSERVATIONS_REQUIRED:
            return PredictionResult(
                product_id=product.id,
                current_score=current,
                direction="stable",
                confidence=0,
                predicted_score_7d=None,
                predicted_score_30d=None,
                prediction_status="insufficient_history",
                methodology="Insufficient historical window (< 3 data points)",
                prediction_version=TrendPredictionService.PREDICTION_VERSION
            )

        momentum = TrendScoringEngine.calculate_momentum(hist_scores)

        # Determine trajectory direction
        if momentum > 0.5 or growth >= 150.0:
            direction = "rising"
            confidence = int(min(65 + (momentum * 4) + (product.sentiment_score * 15) + (len(hist_scores) * 2), 95))
            delta_7d = max(momentum * 1.8, 1.2)
            delta_30d = max(momentum * 3.5, 2.5)
        elif momentum < -0.5 or growth <= 0.0:
            direction = "declining"
            confidence = int(min(60 + abs(momentum * 3) + (len(hist_scores) * 2), 90))
            delta_7d = min(momentum * 1.5, -1.0)
            delta_30d = min(momentum * 3.0, -2.5)
        else:
            direction = "stable"
            confidence = int(min(55 + (product.sentiment_score * 20) + (len(hist_scores) * 2), 85))
            delta_7d = 0.4
            delta_30d = 0.8

        pred_7d = round(min(max(current + delta_7d, 10.0), 99.5), 1)
        pred_30d = round(min(max(current + delta_30d, 10.0), 99.5), 1)

        return PredictionResult(
            product_id=product.id,
            current_score=current,
            direction=direction,
            confidence=confidence,
            predicted_score_7d=pred_7d,
            predicted_score_30d=pred_30d,
            prediction_status="ready",
            horizon_days=30,
            prediction_version=TrendPredictionService.PREDICTION_VERSION
        )
