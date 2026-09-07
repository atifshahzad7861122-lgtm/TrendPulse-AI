import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from backend.app.models.domain import (
    AnomalyDetection, AnomalyCandidate, AnomalyScoreBreakdown, AnomalyObservation
)
from backend.app.services.agents.anomaly_detection.baseline_engine import BaselineStats

class AnomalyScoringEngine:
    """
    Deterministic scoring and evaluation engine for Anomaly Detection.
    Computes 0-100 score and identifies candidate items for human review.
    """

    # Exact documented weights (sum = 1.0)
    WEIGHT_DEVIATION = 0.35
    WEIGHT_CONSISTENCY = 0.25
    WEIGHT_FRESHNESS = 0.15
    WEIGHT_BASELINE_QUALITY = 0.15
    WEIGHT_CROSS_PLATFORM = 0.10

    @classmethod
    def calculate_anomaly_score(
        cls,
        anomalies: List[AnomalyDetection],
        observations: List[AnomalyObservation],
        stats_map: Dict[str, BaselineStats],
        platforms_count: int,
        freshness_status: str
    ) -> Tuple[float, AnomalyScoreBreakdown, str]:
        """
        Calculates composite anomaly score and breakdown.
        """
        if not observations or len(observations) < 2 or not anomalies or freshness_status == "insufficient_data":
            return 0.0, AnomalyScoreBreakdown(
                deviation_magnitude_score=0.0,
                historical_consistency_score=0.0,
                data_freshness_score=0.0,
                baseline_quality_score=0.0,
                cross_platform_score=0.0,
                total_anomaly_score=0.0,
                status="insufficient_data" if len(observations) < 2 else "normal"
            ), "insufficient_data" if len(observations) < 2 else "normal"

        # 1. Deviation Magnitude Score (35%)
        max_severity_scores = {
            "low": 35.0,
            "medium": 65.0,
            "high": 85.0,
            "critical": 100.0
        }
        highest_sev = max(anomalies, key=lambda a: max_severity_scores.get(a.severity, 50.0))
        dev_score = max_severity_scores.get(highest_sev.severity, 50.0)

        # 2. Historical Consistency Score (25%)
        # More observations backing the baseline gives higher statistical reliability
        obs_count = len(observations)
        if obs_count >= 10:
            hist_score = 100.0
        elif obs_count >= 5:
            hist_score = 80.0
        elif obs_count >= 3:
            hist_score = 65.0
        else:
            hist_score = 45.0

        # 3. Data Freshness Score (15%)
        if freshness_status == "fresh":
            fresh_score = 100.0
        elif freshness_status == "recent":
            fresh_score = 70.0
        elif freshness_status == "stale":
            fresh_score = 30.0
        else:
            fresh_score = 0.0

        # 4. Baseline Quality Score (15%)
        # Evaluate MAD / std_dev sanity
        price_stats = stats_map.get("price")
        if price_stats and price_stats.is_sufficient and price_stats.std_dev > 0:
            base_qual_score = 90.0
        elif price_stats and price_stats.is_sufficient:
            base_qual_score = 70.0
        else:
            base_qual_score = 50.0

        # 5. Cross-Platform Confirmation (10%)
        cross_plat_score = 100.0 if platforms_count >= 2 else 50.0

        # Total Composite Score
        total = (
            (dev_score * cls.WEIGHT_DEVIATION) +
            (hist_score * cls.WEIGHT_CONSISTENCY) +
            (fresh_score * cls.WEIGHT_FRESHNESS) +
            (base_qual_score * cls.WEIGHT_BASELINE_QUALITY) +
            (cross_plat_score * cls.WEIGHT_CROSS_PLATFORM)
        )
        total = round(min(100.0, max(0.0, total)), 2)

        breakdown = AnomalyScoreBreakdown(
            deviation_magnitude_score=round(dev_score, 2),
            historical_consistency_score=round(hist_score, 2),
            data_freshness_score=round(fresh_score, 2),
            baseline_quality_score=round(base_qual_score, 2),
            cross_platform_score=round(cross_plat_score, 2),
            total_anomaly_score=total,
            status="anomaly_detected" if total >= 50.0 else "normal"
        )

        return total, breakdown, breakdown.status

    @classmethod
    def evaluate_candidate_qualification(
        cls,
        unified_product_id: str,
        anomalies: List[AnomalyDetection],
        total_score: float,
        confidence: float
    ) -> Optional[AnomalyCandidate]:
        """
        Creates an AnomalyCandidate if an anomaly needs human confirmation
        (e.g., critical severity, low confidence, or unusual discount).
        """
        if not anomalies:
            return None

        # Qualification conditions:
        # 1. Critical severity anomaly
        # 2. Confidence < 0.85
        # 3. Unusual discount or cross-platform price anomaly
        critical_anom = next((a for a in anomalies if a.severity == "critical"), None)
        unusual_disc = next((a for a in anomalies if a.anomaly_type == "unusual_discount"), None)
        low_conf = confidence < 0.85

        if critical_anom or unusual_disc or low_conf:
            primary = critical_anom or unusual_disc or anomalies[0]
            reasons = []
            if critical_anom:
                reasons.append(f"Critical severity {critical_anom.anomaly_type} detected")
            if unusual_disc:
                reasons.append(f"Unusually large observed discount: {unusual_disc.observed_value}%")
            if low_conf:
                reasons.append(f"Moderate confidence ({round(confidence * 100, 1)}%) requires human review")

            return AnomalyCandidate(
                id=f"acand_{uuid.uuid4().hex[:12]}",
                unified_product_id=unified_product_id,
                anomaly_id=primary.id,
                candidate_type=primary.anomaly_type,
                composite_score=total_score,
                confidence=confidence,
                status="pending_review",
                reasons=reasons,
                metadata={
                    "anomaly_type": primary.anomaly_type,
                    "severity": primary.severity,
                    "observed_value": primary.observed_value,
                    "baseline": primary.baseline,
                    "deviation_percent": primary.deviation_percent,
                    "platforms": primary.platforms
                },
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

        return None
