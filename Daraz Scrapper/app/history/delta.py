"""Historical delta engine for calculating exact observation differences."""

from datetime import datetime, timezone
from typing import Optional

from app.history.models import HistoricalObservation, ObservationDeltas


class HistoricalDeltaEngine:
    """
    Computes mathematical and percentage differences between two consecutive
    timestamped product observations.
    """

    @classmethod
    def calculate_deltas(
        cls,
        current_obs: HistoricalObservation,
        previous_obs: Optional[HistoricalObservation],
    ) -> ObservationDeltas:
        """
        Calculate deltas between current and previous observation.
        If previous_obs is None (first observation), returns empty/zero deltas without fabricating data.
        """
        if previous_obs is None:
            return ObservationDeltas(
                time_delta_seconds=0.0,
                time_delta_days=0.0,
                sales_delta=None,
                review_delta=None,
                rating_delta=None,
                price_delta=None,
                sales_pct_change=None,
                review_pct_change=None,
                price_pct_change=None,
            )

        # Elapsed time calculation
        curr_time = current_obs.observed_at
        prev_time = previous_obs.observed_at
        if curr_time.tzinfo is None:
            curr_time = curr_time.replace(tzinfo=timezone.utc)
        if prev_time.tzinfo is None:
            prev_time = prev_time.replace(tzinfo=timezone.utc)

        elapsed_seconds = max(0.0, (curr_time - prev_time).total_seconds())
        elapsed_days = elapsed_seconds / 86400.0

        # 1. Sales Delta
        sales_delta = None
        sales_pct_change = None
        if current_obs.sold_count is not None and previous_obs.sold_count is not None:
            sales_delta = current_obs.sold_count - previous_obs.sold_count
            if previous_obs.sold_count > 0:
                sales_pct_change = round((sales_delta / previous_obs.sold_count) * 100.0, 2)

        # 2. Review Delta
        review_delta = None
        review_pct_change = None
        if current_obs.review_count is not None and previous_obs.review_count is not None:
            review_delta = current_obs.review_count - previous_obs.review_count
            if previous_obs.review_count > 0:
                review_pct_change = round((review_delta / previous_obs.review_count) * 100.0, 2)

        # 3. Price Delta
        price_delta = None
        price_pct_change = None
        if current_obs.price is not None and previous_obs.price is not None:
            price_delta = round(current_obs.price - previous_obs.price, 2)
            if previous_obs.price > 0:
                price_pct_change = round((price_delta / previous_obs.price) * 100.0, 2)

        # 4. Rating Delta
        rating_delta = None
        if current_obs.rating is not None and previous_obs.rating is not None:
            rating_delta = round(current_obs.rating - previous_obs.rating, 2)

        return ObservationDeltas(
            time_delta_seconds=round(elapsed_seconds, 2),
            time_delta_days=round(elapsed_days, 4),
            sales_delta=sales_delta,
            review_delta=review_delta,
            rating_delta=rating_delta,
            price_delta=price_delta,
            sales_pct_change=sales_pct_change,
            review_pct_change=review_pct_change,
            price_pct_change=price_pct_change,
        )
