"""
Deterministic Historical Analytics Engine for Trend Velocity and Growth.

Calculates trend velocity, 7-day growth, and 30-day growth strictly from verified
ProductMarketSnapshot records. Never fabricates or interpolates historical data points.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from backend.app.models.domain import (
    ProductMarketSnapshot, TrendVelocityEvaluation, GrowthEvaluation
)


class HistoricalAnalyticsEngine:
    """
    Evaluates real temporal changes across historical market observations.
    """

    MINIMUM_OBSERVATIONS_FOR_VELOCITY = 2
    MINIMUM_HOURS_DELTA_FOR_VELOCITY = 1.0  # At least 1 hour between points to establish rate of change

    @classmethod
    def calculate_trend_velocity(
        cls,
        snapshots: List[ProductMarketSnapshot],
        metric: str = "review_count"
    ) -> TrendVelocityEvaluation:
        """
        Calculates daily velocity of change for a metric across historical snapshots.
        Returns velocity=None and status='insufficient_data' if fewer than 2 valid observations exist.
        """
        if not snapshots or len(snapshots) < cls.MINIMUM_OBSERVATIONS_FOR_VELOCITY:
            return TrendVelocityEvaluation(
                velocity=None,
                window_days=None,
                status="insufficient_data",
                observation_count=len(snapshots) if snapshots else 0
            )

        # Sort snapshots chronologically
        sorted_snaps = sorted(
            snapshots,
            key=lambda s: s.observed_at if s.observed_at else s.created_at
        )

        oldest = sorted_snaps[0]
        newest = sorted_snaps[-1]

        t_start = oldest.observed_at or oldest.created_at
        t_end = newest.observed_at or newest.created_at

        if not t_start or not t_end:
            return TrendVelocityEvaluation(
                velocity=None,
                window_days=None,
                status="insufficient_data",
                observation_count=len(sorted_snaps)
            )

        # Calculate time delta in days
        delta_seconds = (t_end - t_start).total_seconds()
        delta_hours = delta_seconds / 3600.0

        if delta_hours < cls.MINIMUM_HOURS_DELTA_FOR_VELOCITY:
            return TrendVelocityEvaluation(
                velocity=None,
                window_days=round(delta_seconds / 86400.0, 3),
                status="insufficient_data",
                observation_count=len(sorted_snaps)
            )

        delta_days = delta_seconds / 86400.0

        # Extract metric values
        if metric == "price":
            v_start = oldest.price
            v_end = newest.price
        elif metric == "rating":
            v_start = oldest.rating
            v_end = newest.rating
        else:  # default: review_count
            v_start = float(oldest.review_count)
            v_end = float(newest.review_count)

        # Daily rate of change
        rate_of_change = (v_end - v_start) / delta_days
        velocity = round(rate_of_change, 3)

        return TrendVelocityEvaluation(
            velocity=velocity,
            window_days=round(delta_days, 2),
            status="calculated",
            observation_count=len(sorted_snaps)
        )

    @classmethod
    def calculate_growth(
        cls,
        snapshots: List[ProductMarketSnapshot],
        metric: str = "review_count"
    ) -> GrowthEvaluation:
        """
        Calculates 7-day and 30-day percentage growth relative to observed baseline snapshots.
        If snapshots do not span the requested window, returns None for that window.
        """
        if not snapshots or len(snapshots) < 2:
            return GrowthEvaluation(
                growth_7d=None,
                growth_30d=None,
                window_days=None,
                status="insufficient_data",
                observation_count=len(snapshots) if snapshots else 0
            )

        sorted_snaps = sorted(
            snapshots,
            key=lambda s: s.observed_at if s.observed_at else s.created_at
        )

        newest = sorted_snaps[-1]
        now_dt = newest.observed_at or newest.created_at or datetime.now(timezone.utc)

        def get_val(s: ProductMarketSnapshot) -> float:
            if metric == "price":
                return s.price
            elif metric == "rating":
                return s.rating
            return float(s.review_count)

        v_newest = get_val(newest)

        # Find candidate closest to 7 days ago (between 5 and 10 days)
        cand_7d = None
        min_diff_7d = float("inf")
        target_7d = now_dt - timedelta(days=7)

        # Find candidate closest to 30 days ago (between 25 and 35 days)
        cand_30d = None
        min_diff_30d = float("inf")
        target_30d = now_dt - timedelta(days=30)

        for s in sorted_snaps[:-1]:
            s_dt = s.observed_at or s.created_at
            if not s_dt:
                continue

            diff_7 = abs((s_dt - target_7d).total_seconds())
            if diff_7 < (3 * 86400) and diff_7 < min_diff_7d:
                min_diff_7d = diff_7
                cand_7d = s

            diff_30 = abs((s_dt - target_30d).total_seconds())
            if diff_30 < (5 * 86400) and diff_30 < min_diff_30d:
                min_diff_30d = diff_30
                cand_30d = s

        growth_7d = None
        if cand_7d:
            v_7 = get_val(cand_7d)
            if v_7 > 0:
                growth_7d = round(((v_newest - v_7) / v_7) * 100.0, 1)

        growth_30d = None
        if cand_30d:
            v_30 = get_val(cand_30d)
            if v_30 > 0:
                growth_30d = round(((v_newest - v_30) / v_30) * 100.0, 1)

        oldest = sorted_snaps[0]
        t_start = oldest.observed_at or oldest.created_at
        total_window = round((now_dt - t_start).total_seconds() / 86400.0, 2) if t_start else None

        status = "calculated" if (growth_7d is not None or growth_30d is not None) else "insufficient_data"

        return GrowthEvaluation(
            growth_7d=growth_7d,
            growth_30d=growth_30d,
            window_days=total_window,
            status=status,
            observation_count=len(sorted_snaps)
        )
