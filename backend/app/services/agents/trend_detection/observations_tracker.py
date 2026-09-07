import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from backend.app.models.domain import TrendObservation, UnifiedProduct, ProductPlatformListing

class ObservationsTracker:
    """
    Tracks and records historical metric observations across marketplaces.
    Calculates deltas, percentage changes, and observation data freshness.
    """

    FRESH_DAYS = 7
    RECENT_DAYS = 14
    STALE_DAYS = 30

    @staticmethod
    def calculate_freshness(observations: List[TrendObservation]) -> str:
        """
        Determines dataset freshness based on the most recent observation timestamp.
        Returns: 'fresh', 'recent', 'stale', or 'insufficient_data'
        """
        if not observations:
            return "insufficient_data"

        now = datetime.now(timezone.utc)
        latest_obs = max(observations, key=lambda o: o.observed_at)
        age = now - latest_obs.observed_at

        if age <= timedelta(days=ObservationsTracker.FRESH_DAYS):
            return "fresh"
        elif age <= timedelta(days=ObservationsTracker.RECENT_DAYS):
            return "recent"
        elif age <= timedelta(days=ObservationsTracker.STALE_DAYS):
            return "stale"
        else:
            return "stale"

    @staticmethod
    def build_observations_from_listing(
        unified_product_id: str,
        listing: Dict[str, Any],
        prior_observations: List[TrendObservation]
    ) -> List[TrendObservation]:
        """
        Generates TrendObservation items for an incoming product listing by comparing against prior observations.
        Supported metrics: price, rating, review_count, availability
        """
        now = datetime.now(timezone.utc)
        platform = str(listing.get("platform", "unknown")).lower()
        new_obs: List[TrendObservation] = []

        # 1. Price observation
        price = listing.get("price")
        if price is not None:
            try:
                price_val = float(price)
                if price_val >= 0:
                    prior_price = ObservationsTracker._find_latest_metric(
                        prior_observations, platform=platform, metric_type="price"
                    )
                    prev_val = prior_price.metric_value if prior_price else None
                    chg_val = round(price_val - prev_val, 2) if prev_val is not None else None
                    chg_pct = round(((price_val - prev_val) / prev_val) * 100, 2) if prev_val and prev_val > 0 else None

                    new_obs.append(TrendObservation(
                        id=f"obs_prc_{uuid.uuid4().hex[:12]}",
                        unified_product_id=unified_product_id,
                        platform=platform,
                        metric_type="price",
                        metric_value=price_val,
                        previous_value=prev_val,
                        change_value=chg_val,
                        change_percent=chg_pct,
                        observed_at=now,
                        source=f"{platform}_sync",
                        metadata={"currency": listing.get("currency", "PKR")},
                        created_at=now
                    ))
            except (ValueError, TypeError):
                pass

        # 2. Rating observation
        rating = listing.get("rating")
        if rating is not None:
            try:
                rating_val = float(rating)
                if 0.0 <= rating_val <= 5.0:
                    prior_rating = ObservationsTracker._find_latest_metric(
                        prior_observations, platform=platform, metric_type="rating"
                    )
                    prev_val = prior_rating.metric_value if prior_rating else None
                    chg_val = round(rating_val - prev_val, 2) if prev_val is not None else None
                    chg_pct = round(((rating_val - prev_val) / prev_val) * 100, 2) if prev_val and prev_val > 0 else None

                    new_obs.append(TrendObservation(
                        id=f"obs_rtg_{uuid.uuid4().hex[:12]}",
                        unified_product_id=unified_product_id,
                        platform=platform,
                        metric_type="rating",
                        metric_value=rating_val,
                        previous_value=prev_val,
                        change_value=chg_val,
                        change_percent=chg_pct,
                        observed_at=now,
                        source=f"{platform}_sync",
                        metadata={},
                        created_at=now
                    ))
            except (ValueError, TypeError):
                pass

        # 3. Review Count observation
        reviews = listing.get("review_count") or listing.get("reviews") or listing.get("total_reviews")
        if reviews is not None:
            try:
                rev_val = float(reviews)
                if rev_val >= 0:
                    prior_rev = ObservationsTracker._find_latest_metric(
                        prior_observations, platform=platform, metric_type="review_count"
                    )
                    prev_val = prior_rev.metric_value if prior_rev else None
                    chg_val = rev_val - prev_val if prev_val is not None else None
                    chg_pct = round(((rev_val - prev_val) / prev_val) * 100, 2) if prev_val and prev_val > 0 else None

                    new_obs.append(TrendObservation(
                        id=f"obs_rev_{uuid.uuid4().hex[:12]}",
                        unified_product_id=unified_product_id,
                        platform=platform,
                        metric_type="review_count",
                        metric_value=rev_val,
                        previous_value=prev_val,
                        change_value=chg_val,
                        change_percent=chg_pct,
                        observed_at=now,
                        source=f"{platform}_sync",
                        metadata={},
                        created_at=now
                    ))
            except (ValueError, TypeError):
                pass

        # 4. Availability observation
        avail = listing.get("available") or listing.get("availability") or listing.get("is_available")
        if avail is not None:
            avail_val = 1.0 if (avail is True or str(avail).lower() in ["true", "1", "available"]) else 0.0
            prior_avail = ObservationsTracker._find_latest_metric(
                prior_observations, platform=platform, metric_type="availability"
            )
            prev_val = prior_avail.metric_value if prior_avail else None
            chg_val = avail_val - prev_val if prev_val is not None else None

            new_obs.append(TrendObservation(
                id=f"obs_avl_{uuid.uuid4().hex[:12]}",
                unified_product_id=unified_product_id,
                platform=platform,
                metric_type="availability",
                metric_value=avail_val,
                previous_value=prev_val,
                change_value=chg_val,
                change_percent=None,
                observed_at=now,
                source=f"{platform}_sync",
                metadata={"status": "in_stock" if avail_val == 1.0 else "out_of_stock"},
                created_at=now
            ))

        return new_obs

    @staticmethod
    def _find_latest_metric(
        observations: List[TrendObservation],
        platform: str,
        metric_type: str
    ) -> Optional[TrendObservation]:
        """Finds the most recent observation matching platform and metric_type."""
        matches = [
            o for o in observations
            if o.platform.lower() == platform.lower() and o.metric_type == metric_type
        ]
        if not matches:
            return None
        return max(matches, key=lambda o: o.observed_at)
