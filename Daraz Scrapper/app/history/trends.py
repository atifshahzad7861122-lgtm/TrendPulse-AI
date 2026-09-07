"""Trend engine for calculating normalized trend scores and direction signals."""

from datetime import datetime, timezone
from typing import List, Optional

from app.history.models import HistoricalObservation, TrendScore, TrendSignal
from app.history.velocity import SalesVelocityEngine


class TrendEngine:
    """
    Analyzes historical product observation time-series to detect growth trends,
    sales acceleration, review spikes, and rating health.
    """

    RISING_THRESHOLD = 65.0
    DECLINING_THRESHOLD = 35.0
    MIN_OBSERVATIONS_FOR_TREND = 2
    MIN_WINDOW_HOURS = 1.0

    @classmethod
    def analyze_trend(
        cls,
        observations: List[HistoricalObservation],
        min_hours: float = 1.0,
    ) -> TrendScore:
        """
        Evaluate time series observations and produce a normalized TrendScore (0-100)
        and TrendSignal (RISING, STABLE, DECLINING, INSUFFICIENT_DATA).
        """
        if not observations or len(observations) < cls.MIN_OBSERVATIONS_FOR_TREND:
            return TrendScore(
                score=0.0,
                signal=TrendSignal.INSUFFICIENT_DATA,
                confidence=0.0,
                velocity=None,
                observation_count=len(observations) if observations else 0,
                summary="Insufficient data: Minimum 2 historical observations required.",
            )

        sorted_obs = sorted(observations, key=lambda o: o.observed_at)
        first_obs = sorted_obs[0]
        latest_obs = sorted_obs[-1]

        t_start = first_obs.observed_at
        t_end = latest_obs.observed_at
        if t_start.tzinfo is None:
            t_start = t_start.replace(tzinfo=timezone.utc)
        if t_end.tzinfo is None:
            t_end = t_end.replace(tzinfo=timezone.utc)

        span_hours = (t_end - t_start).total_seconds() / 3600.0
        if span_hours < min_hours:
            return TrendScore(
                score=0.0,
                signal=TrendSignal.INSUFFICIENT_DATA,
                confidence=0.1,
                velocity=None,
                observation_count=len(sorted_obs),
                summary=f"Insufficient time span: {round(span_hours, 2)} hours elapsed (minimum {min_hours}h needed).",
            )

        # Compute underlying velocities
        velocity = SalesVelocityEngine.calculate_velocity_from_observations(sorted_obs)

        # Baseline starting score
        score = 50.0

        # Factor 1: Sales Velocity (40% Weight)
        if velocity.sales_per_day is not None:
            if velocity.sales_per_day > 50:
                score += 35.0
            elif velocity.sales_per_day > 10:
                score += 25.0
            elif velocity.sales_per_day > 1:
                score += 15.0
            elif velocity.sales_per_day > 0:
                score += 5.0
            elif velocity.sales_per_day < 0:
                score -= 20.0

        # Factor 2: Review Growth (25% Weight)
        if velocity.review_growth_rate_per_day is not None:
            if velocity.review_growth_rate_per_day > 5:
                score += 20.0
            elif velocity.review_growth_rate_per_day > 1:
                score += 12.0
            elif velocity.review_growth_rate_per_day > 0:
                score += 5.0

        # Factor 3: Rating Health & Stability (15% Weight)
        if latest_obs.rating is not None and first_obs.rating is not None:
            rating_diff = latest_obs.rating - first_obs.rating
            if latest_obs.rating >= 4.5:
                score += 10.0
            elif latest_obs.rating >= 4.0:
                score += 5.0
            elif latest_obs.rating < 3.0:
                score -= 15.0

            if rating_diff > 0.2:
                score += 5.0
            elif rating_diff < -0.2:
                score -= 10.0

        # Factor 4: Stock Availability (10% Weight)
        if not latest_obs.availability:
            score -= 20.0
        else:
            score += 5.0

        # Factor 5: Price Attractiveness / Discount (10% Weight)
        if latest_obs.discount and latest_obs.discount > 10:
            score += 5.0

        # Clamp score between 0.0 and 100.0
        final_score = max(0.0, min(100.0, round(score, 1)))

        # Assign signal
        if final_score >= cls.RISING_THRESHOLD:
            signal = TrendSignal.RISING
            summary = f"Rising trend: Strong sales velocity ({velocity.sales_per_day or 0}/day) and review engagement."
        elif final_score <= cls.DECLINING_THRESHOLD:
            signal = TrendSignal.DECLINING
            summary = f"Declining trend: Low/negative momentum or stock/rating degradation."
        else:
            signal = TrendSignal.STABLE
            summary = f"Stable trend: Consistent pricing and steady baseline activity."

        confidence = min(1.0, 0.5 + (len(sorted_obs) * 0.05) + min(0.3, span_hours / 168.0))

        return TrendScore(
            score=final_score,
            signal=signal,
            confidence=round(confidence, 2),
            velocity=velocity,
            observation_count=len(sorted_obs),
            summary=summary,
        )
