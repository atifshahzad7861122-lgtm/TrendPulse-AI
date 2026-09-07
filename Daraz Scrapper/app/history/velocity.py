"""Sales velocity engine for computing time-normalized sales and review rates."""

from datetime import datetime, timezone
from typing import List, Optional

from app.history.models import HistoricalObservation, VelocityMetrics


class SalesVelocityEngine:
    """
    Computes time-normalized rates of change (sales per day, 7-day velocity, 30-day velocity,
    review growth per day) across a series of timestamped observations.
    """

    @classmethod
    def calculate_velocity_from_observations(
        cls, observations: List[HistoricalObservation]
    ) -> VelocityMetrics:
        """
        Calculate aggregate velocity metrics from a chronological list of observations.
        Requires at least 2 observations with measurable time delta.
        """
        if not observations or len(observations) < 2:
            return VelocityMetrics(
                sales_per_day=None,
                sales_per_7_days=None,
                sales_per_30_days=None,
                review_growth_rate_per_day=None,
                price_change_rate=None,
                window_days=0.0,
                observation_count=len(observations) if observations else 0,
            )

        # Sort chronologically
        sorted_obs = sorted(observations, key=lambda o: o.observed_at)
        first_obs = sorted_obs[0]
        latest_obs = sorted_obs[-1]

        t_start = first_obs.observed_at
        t_end = latest_obs.observed_at
        if t_start.tzinfo is None:
            t_start = t_start.replace(tzinfo=timezone.utc)
        if t_end.tzinfo is None:
            t_end = t_end.replace(tzinfo=timezone.utc)

        total_seconds = max(0.0, (t_end - t_start).total_seconds())
        window_days = total_seconds / 86400.0

        if window_days <= 0.0:
            return VelocityMetrics(
                sales_per_day=None,
                sales_per_7_days=None,
                sales_per_30_days=None,
                review_growth_rate_per_day=None,
                price_change_rate=None,
                window_days=0.0,
                observation_count=len(sorted_obs),
            )

        # 1. Sales Velocity
        sales_per_day = None
        sales_per_7_days = None
        sales_per_30_days = None
        if latest_obs.sold_count is not None and first_obs.sold_count is not None:
            net_sales = latest_obs.sold_count - first_obs.sold_count
            sales_per_day = round(net_sales / window_days, 2)
            sales_per_7_days = round(sales_per_day * 7.0, 2)
            sales_per_30_days = round(sales_per_day * 30.0, 2)

        # 2. Review Velocity
        review_growth_rate = None
        if latest_obs.review_count is not None and first_obs.review_count is not None:
            net_reviews = latest_obs.review_count - first_obs.review_count
            review_growth_rate = round(net_reviews / window_days, 2)

        # 3. Price Change Rate
        price_rate = None
        if latest_obs.price is not None and first_obs.price is not None:
            net_price = latest_obs.price - first_obs.price
            price_rate = round(net_price / window_days, 2)

        return VelocityMetrics(
            sales_per_day=sales_per_day,
            sales_per_7_days=sales_per_7_days,
            sales_per_30_days=sales_per_30_days,
            review_growth_rate_per_day=review_growth_rate,
            price_change_rate=price_rate,
            window_days=round(window_days, 2),
            observation_count=len(sorted_obs),
        )
