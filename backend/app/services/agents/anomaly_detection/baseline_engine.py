import uuid
import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from backend.app.models.domain import AnomalyObservation

class BaselineStats(BaseModel):
    metric_type: str
    count: int
    mean: float
    median: float
    std_dev: float
    mad: float  # Median Absolute Deviation
    min_val: float
    max_val: float
    latest_val: float
    freshness: str  # fresh, recent, stale, insufficient_data
    is_sufficient: bool

class BaselineEngine:
    """
    Statistical baseline computation engine for Anomaly Detection.
    Computes rolling mean, median, standard deviation, and MAD (Median Absolute Deviation).
    Enforces strict anti-fabrication gates when observations are sparse.
    """

    FRESH_DAYS = 7
    RECENT_DAYS = 14
    STALE_DAYS = 30
    MIN_OBSERVATIONS_FOR_STATS = 3
    MIN_OBSERVATIONS_FOR_DELTA = 2

    @classmethod
    def calculate_freshness(cls, observations: List[AnomalyObservation]) -> str:
        if not observations:
            return "insufficient_data"
        now = datetime.now(timezone.utc)
        latest_time = max(
            obs.observed_at if obs.observed_at.tzinfo else obs.observed_at.replace(tzinfo=timezone.utc)
            for obs in observations
        )
        age_days = (now - latest_time).total_seconds() / 86400.0
        if age_days <= cls.FRESH_DAYS:
            return "fresh"
        elif age_days <= cls.RECENT_DAYS:
            return "recent"
        elif age_days <= cls.STALE_DAYS:
            return "stale"
        else:
            return "stale"

    @classmethod
    def compute_baseline(
        cls,
        observations: List[AnomalyObservation],
        metric_type: str
    ) -> BaselineStats:
        """
        Computes baseline statistics for a specific metric over historical observations.
        """
        filtered = [o for o in observations if o.metric_type.lower() == metric_type.lower()]
        if not filtered:
            return BaselineStats(
                metric_type=metric_type,
                count=0,
                mean=0.0,
                median=0.0,
                std_dev=0.0,
                mad=0.0,
                min_val=0.0,
                max_val=0.0,
                latest_val=0.0,
                freshness="insufficient_data",
                is_sufficient=False
            )

        # Sort chronological
        sorted_obs = sorted(filtered, key=lambda x: x.observed_at)
        values = [float(o.metric_value) for o in sorted_obs]
        n = len(values)
        freshness = cls.calculate_freshness(filtered)

        if n < cls.MIN_OBSERVATIONS_FOR_DELTA or freshness == "insufficient_data":
            latest = values[-1] if values else 0.0
            return BaselineStats(
                metric_type=metric_type,
                count=n,
                mean=latest,
                median=latest,
                std_dev=0.0,
                mad=0.0,
                min_val=latest,
                max_val=latest,
                latest_val=latest,
                freshness=freshness,
                is_sufficient=False
            )

        mean_val = sum(values) / n
        median_val = cls._calculate_median(values)

        # Variance & Std Dev
        variance = sum((x - mean_val) ** 2 for x in values) / n if n > 0 else 0.0
        std_dev = math.sqrt(variance)

        # Median Absolute Deviation (MAD)
        abs_deviations = [abs(x - median_val) for x in values]
        mad = cls._calculate_median(abs_deviations)

        return BaselineStats(
            metric_type=metric_type,
            count=n,
            mean=round(mean_val, 4),
            median=round(median_val, 4),
            std_dev=round(std_dev, 4),
            mad=round(mad, 4),
            min_val=min(values),
            max_val=max(values),
            latest_val=values[-1],
            freshness=freshness,
            is_sufficient=True
        )

    @classmethod
    def build_observations_from_listing(
        cls,
        unified_product_id: str,
        listing: Dict[str, Any],
        prior_observations: Optional[List[AnomalyObservation]] = None
    ) -> List[AnomalyObservation]:
        """
        Creates timestamped AnomalyObservation records from incoming listing payloads
        while calculating real delta changes against prior observations.
        """
        prior_observations = prior_observations or []
        now = datetime.now(timezone.utc)
        platform = str(listing.get("platform", "unknown")).lower()
        results: List[AnomalyObservation] = []

        # 1. Price
        if "price" in listing and listing["price"] is not None:
            price_val = float(listing["price"])
            prev_price = cls._find_latest_prior(prior_observations, "price", platform)
            change_val = (price_val - prev_price) if prev_price is not None else None
            change_pct = ((price_val - prev_price) / prev_price * 100.0) if prev_price and prev_price > 0 else None

            results.append(AnomalyObservation(
                id=f"aobs_prc_{uuid.uuid4().hex[:12]}",
                unified_product_id=unified_product_id,
                platform=platform,
                metric_type="price",
                metric_value=price_val,
                previous_value=prev_price,
                change_value=round(change_val, 4) if change_val is not None else None,
                change_percent=round(change_pct, 4) if change_pct is not None else None,
                observed_at=now,
                metadata_json={"currency": listing.get("currency", "USD")}
            ))

        # 2. Rating
        if "rating" in listing and listing["rating"] is not None:
            rating_val = float(listing["rating"])
            prev_rating = cls._find_latest_prior(prior_observations, "rating", platform)
            change_val = (rating_val - prev_rating) if prev_rating is not None else None
            change_pct = ((rating_val - prev_rating) / prev_rating * 100.0) if prev_rating and prev_rating > 0 else None

            results.append(AnomalyObservation(
                id=f"aobs_rtg_{uuid.uuid4().hex[:12]}",
                unified_product_id=unified_product_id,
                platform=platform,
                metric_type="rating",
                metric_value=rating_val,
                previous_value=prev_rating,
                change_value=round(change_val, 4) if change_val is not None else None,
                change_percent=round(change_pct, 4) if change_pct is not None else None,
                observed_at=now
            ))

        # 3. Review Count
        if "review_count" in listing and listing["review_count"] is not None:
            rev_val = float(listing["review_count"])
            prev_rev = cls._find_latest_prior(prior_observations, "review_count", platform)
            change_val = (rev_val - prev_rev) if prev_rev is not None else None
            change_pct = ((rev_val - prev_rev) / prev_rev * 100.0) if prev_rev and prev_rev > 0 else None

            results.append(AnomalyObservation(
                id=f"aobs_rev_{uuid.uuid4().hex[:12]}",
                unified_product_id=unified_product_id,
                platform=platform,
                metric_type="review_count",
                metric_value=rev_val,
                previous_value=prev_rev,
                change_value=round(change_val, 4) if change_val is not None else None,
                change_percent=round(change_pct, 4) if change_pct is not None else None,
                observed_at=now
            ))

        # 4. Availability
        if "available" in listing and listing["available"] is not None:
            avail_val = 1.0 if listing["available"] else 0.0
            prev_avail = cls._find_latest_prior(prior_observations, "availability", platform)
            results.append(AnomalyObservation(
                id=f"aobs_avl_{uuid.uuid4().hex[:12]}",
                unified_product_id=unified_product_id,
                platform=platform,
                metric_type="availability",
                metric_value=avail_val,
                previous_value=prev_avail,
                change_value=(avail_val - prev_avail) if prev_avail is not None else None,
                change_percent=None,
                observed_at=now
            ))

        # 5. Discount
        if "discount_percentage" in listing and listing["discount_percentage"] is not None:
            disc_val = float(listing["discount_percentage"])
            prev_disc = cls._find_latest_prior(prior_observations, "discount", platform)
            results.append(AnomalyObservation(
                id=f"aobs_dsc_{uuid.uuid4().hex[:12]}",
                unified_product_id=unified_product_id,
                platform=platform,
                metric_type="discount",
                metric_value=disc_val,
                previous_value=prev_disc,
                change_value=(disc_val - prev_disc) if prev_disc is not None else None,
                change_percent=None,
                observed_at=now
            ))

        return results

    @staticmethod
    def _calculate_median(numbers: List[float]) -> float:
        if not numbers:
            return 0.0
        sorted_nums = sorted(numbers)
        length = len(sorted_nums)
        mid = length // 2
        if length % 2 == 0:
            return (sorted_nums[mid - 1] + sorted_nums[mid]) / 2.0
        else:
            return sorted_nums[mid]

    @staticmethod
    def _find_latest_prior(
        observations: List[AnomalyObservation],
        metric_type: str,
        platform: str
    ) -> Optional[float]:
        matching = [
            o for o in observations
            if o.metric_type.lower() == metric_type.lower() and o.platform.lower() == platform.lower()
        ]
        if not matching:
            return None
        matching.sort(key=lambda x: x.observed_at, reverse=True)
        return float(matching[0].metric_value)
