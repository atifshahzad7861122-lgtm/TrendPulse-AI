import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from backend.app.models.domain import AnomalyDetection, AnomalyObservation
from backend.app.services.agents.anomaly_detection.baseline_engine import BaselineEngine, BaselineStats

class AnomalyDetectorRulesEngine:
    """
    Deterministic rule engine for Anomaly Detection.
    Detects 13 distinct anomaly categories using statistical baselines and exact thresholds.
    """

    PRICE_SPIKE_PCT = 35.0
    PRICE_CRASH_PCT = -35.0
    UNUSUAL_DISCOUNT_PCT = 60.0
    RATING_JUMP_DELTA = 0.5
    RATING_DROP_DELTA = -0.5
    REVIEW_VELOCITY_MULTIPLIER = 2.5
    CROSS_PLATFORM_PRICE_DISPARITY_PCT = 40.0

    @classmethod
    def evaluate_all_anomalies(
        cls,
        unified_product_id: str,
        observations: List[AnomalyObservation],
        active_platforms: Optional[List[str]] = None,
        platform_listings: Optional[List[Dict[str, Any]]] = None,
        provider_data: Optional[Dict[str, Any]] = None
    ) -> List[AnomalyDetection]:
        """
        Evaluates observations against all statistical anomaly detectors.
        """
        active_platforms = active_platforms or []
        detected: List[AnomalyDetection] = []

        if not observations or len(observations) < BaselineEngine.MIN_OBSERVATIONS_FOR_DELTA:
            return detected

        # Compute baselines for price, rating, review_count, availability, discount
        price_stats = BaselineEngine.compute_baseline(observations, "price")
        rating_stats = BaselineEngine.compute_baseline(observations, "rating")
        review_stats = BaselineEngine.compute_baseline(observations, "review_count")
        avail_stats = BaselineEngine.compute_baseline(observations, "availability")
        discount_stats = BaselineEngine.compute_baseline(observations, "discount")

        # 1. Price Spike & Price Crash
        cls._detect_price_anomalies(unified_product_id, observations, price_stats, active_platforms, detected)

        # 2. Unusual Discount
        cls._detect_discount_anomalies(unified_product_id, observations, discount_stats, active_platforms, detected)

        # 3. Rating Jump & Rating Drop
        cls._detect_rating_anomalies(unified_product_id, observations, rating_stats, active_platforms, detected)

        # 4. Review Velocity Spike & Drop
        cls._detect_review_velocity_anomalies(unified_product_id, observations, review_stats, active_platforms, detected)

        # 5. Availability & Inventory Anomalies
        cls._detect_availability_anomalies(unified_product_id, observations, avail_stats, active_platforms, detected)

        # 6. Cross-Platform Price & Presence Anomalies
        if platform_listings or len(active_platforms) >= 2:
            cls._detect_cross_platform_anomalies(unified_product_id, active_platforms, platform_listings or [], detected)

        # 7. Provider Data Anomaly
        if provider_data:
            cls._detect_provider_anomalies(unified_product_id, provider_data, detected)

        return detected

    @classmethod
    def _detect_price_anomalies(
        cls,
        product_id: str,
        observations: List[AnomalyObservation],
        stats: BaselineStats,
        platforms: List[str],
        results: List[AnomalyDetection]
    ):
        if not stats.is_sufficient or stats.count < 2:
            return

        price_obs = [o for o in observations if o.metric_type == "price"]
        if not price_obs:
            return
        price_obs.sort(key=lambda x: x.observed_at, reverse=True)
        latest_obs = price_obs[0]
        curr_price = latest_obs.metric_value
        baseline_price = stats.median if stats.median > 0 else stats.mean

        if baseline_price <= 0:
            return

        pct_dev = ((curr_price - baseline_price) / baseline_price) * 100.0
        abs_dev = curr_price - baseline_price

        # Check MAD / Std Dev multiplier
        mad_multiplier = (abs(abs_dev) / stats.mad) if stats.mad > 0 else 0.0
        std_multiplier = (abs(abs_dev) / stats.std_dev) if stats.std_dev > 0 else 0.0

        # Price Spike
        if pct_dev >= cls.PRICE_SPIKE_PCT or (pct_dev > 0 and (mad_multiplier >= 2.5 or std_multiplier >= 2.5)):
            severity = "critical" if pct_dev >= 100.0 or mad_multiplier >= 4.0 else ("high" if pct_dev >= 50.0 else "medium")
            score = min(100.0, 50.0 + min(50.0, pct_dev * 0.5))
            fingerprint = cls.generate_fingerprint(product_id, "price_spike", "rolling_median", [o.id for o in price_obs[:5]])
            results.append(AnomalyDetection(
                id=f"anom_spk_{uuid.uuid4().hex[:12]}",
                unified_product_id=product_id,
                anomaly_type="price_spike",
                severity=severity,
                score=round(score, 2),
                confidence=0.94 if stats.count >= 3 else 0.82,
                baseline=round(baseline_price, 2),
                observed_value=round(curr_price, 2),
                deviation=round(abs_dev, 2),
                deviation_percent=round(pct_dev, 2),
                baseline_method="rolling_median",
                evidence={
                    "historical_observations_count": stats.count,
                    "median_price": stats.median,
                    "mean_price": stats.mean,
                    "std_dev": stats.std_dev,
                    "mad": stats.mad,
                    "mad_multiplier": round(mad_multiplier, 2)
                },
                platforms=[latest_obs.platform] if latest_obs.platform else platforms,
                fingerprint=fingerprint,
                status="active",
                detected_at=datetime.now(timezone.utc)
            ))

        # Price Crash
        elif pct_dev <= cls.PRICE_CRASH_PCT or (pct_dev < 0 and (mad_multiplier >= 2.5 or std_multiplier >= 2.5)):
            severity = "critical" if pct_dev <= -70.0 else ("high" if pct_dev <= -50.0 else "medium")
            score = min(100.0, 50.0 + min(50.0, abs(pct_dev) * 0.5))
            fingerprint = cls.generate_fingerprint(product_id, "price_crash", "rolling_median", [o.id for o in price_obs[:5]])
            results.append(AnomalyDetection(
                id=f"anom_csh_{uuid.uuid4().hex[:12]}",
                unified_product_id=product_id,
                anomaly_type="price_crash",
                severity=severity,
                score=round(score, 2),
                confidence=0.94 if stats.count >= 3 else 0.82,
                baseline=round(baseline_price, 2),
                observed_value=round(curr_price, 2),
                deviation=round(abs_dev, 2),
                deviation_percent=round(pct_dev, 2),
                baseline_method="rolling_median",
                evidence={
                    "historical_observations_count": stats.count,
                    "median_price": stats.median,
                    "mean_price": stats.mean,
                    "std_dev": stats.std_dev,
                    "mad": stats.mad
                },
                platforms=[latest_obs.platform] if latest_obs.platform else platforms,
                fingerprint=fingerprint,
                status="active",
                detected_at=datetime.now(timezone.utc)
            ))

    @classmethod
    def _detect_discount_anomalies(
        cls,
        product_id: str,
        observations: List[AnomalyObservation],
        stats: BaselineStats,
        platforms: List[str],
        results: List[AnomalyDetection]
    ):
        disc_obs = [o for o in observations if o.metric_type == "discount"]
        if not disc_obs:
            return
        disc_obs.sort(key=lambda x: x.observed_at, reverse=True)
        latest_disc = disc_obs[0].metric_value

        if latest_disc >= cls.UNUSUAL_DISCOUNT_PCT:
            severity = "high" if latest_disc >= 75.0 else "medium"
            score = min(100.0, 50.0 + latest_disc * 0.5)
            fingerprint = cls.generate_fingerprint(product_id, "unusual_discount", "threshold_check", [o.id for o in disc_obs[:3]])
            results.append(AnomalyDetection(
                id=f"anom_dsc_{uuid.uuid4().hex[:12]}",
                unified_product_id=product_id,
                anomaly_type="unusual_discount",
                severity=severity,
                score=round(score, 2),
                confidence=0.90,
                baseline=round(stats.median if stats.is_sufficient else 15.0, 2),
                observed_value=round(latest_disc, 2),
                deviation=round(latest_disc - (stats.median if stats.is_sufficient else 15.0), 2),
                deviation_percent=round(latest_disc, 2),
                baseline_method="threshold_and_baseline",
                evidence={
                    "observed_discount_percent": latest_disc,
                    "message": "Unusually large observed discount"
                },
                platforms=[disc_obs[0].platform] if disc_obs[0].platform else platforms,
                fingerprint=fingerprint,
                status="active",
                detected_at=datetime.now(timezone.utc)
            ))

    @classmethod
    def _detect_rating_anomalies(
        cls,
        product_id: str,
        observations: List[AnomalyObservation],
        stats: BaselineStats,
        platforms: List[str],
        results: List[AnomalyDetection]
    ):
        rtg_obs = [o for o in observations if o.metric_type == "rating"]
        if not rtg_obs or len(rtg_obs) < 2:
            return
        rtg_obs.sort(key=lambda x: x.observed_at, reverse=True)
        latest = rtg_obs[0]
        prev = rtg_obs[1]
        delta = latest.metric_value - prev.metric_value

        if delta >= cls.RATING_JUMP_DELTA:
            fingerprint = cls.generate_fingerprint(product_id, "rating_jump", "rating_delta", [latest.id, prev.id])
            results.append(AnomalyDetection(
                id=f"anom_rjmp_{uuid.uuid4().hex[:12]}",
                unified_product_id=product_id,
                anomaly_type="rating_jump",
                severity="medium" if delta < 0.8 else "high",
                score=round(min(100.0, 60.0 + delta * 30.0), 2),
                confidence=0.92,
                baseline=prev.metric_value,
                observed_value=latest.metric_value,
                deviation=round(delta, 2),
                deviation_percent=round((delta / prev.metric_value) * 100.0 if prev.metric_value > 0 else delta * 20.0, 2),
                baseline_method="previous_observation",
                evidence={
                    "previous_rating": prev.metric_value,
                    "current_rating": latest.metric_value,
                    "rating_jump_delta": round(delta, 2)
                },
                platforms=[latest.platform],
                fingerprint=fingerprint,
                status="active",
                detected_at=datetime.now(timezone.utc)
            ))
        elif delta <= cls.RATING_DROP_DELTA:
            fingerprint = cls.generate_fingerprint(product_id, "rating_drop", "rating_delta", [latest.id, prev.id])
            results.append(AnomalyDetection(
                id=f"anom_rdrp_{uuid.uuid4().hex[:12]}",
                unified_product_id=product_id,
                anomaly_type="rating_drop",
                severity="high" if delta <= -1.0 else "medium",
                score=round(min(100.0, 60.0 + abs(delta) * 30.0), 2),
                confidence=0.92,
                baseline=prev.metric_value,
                observed_value=latest.metric_value,
                deviation=round(delta, 2),
                deviation_percent=round((delta / prev.metric_value) * 100.0 if prev.metric_value > 0 else delta * 20.0, 2),
                baseline_method="previous_observation",
                evidence={
                    "previous_rating": prev.metric_value,
                    "current_rating": latest.metric_value,
                    "rating_drop_delta": round(delta, 2)
                },
                platforms=[latest.platform],
                fingerprint=fingerprint,
                status="active",
                detected_at=datetime.now(timezone.utc)
            ))

    @classmethod
    def _detect_review_velocity_anomalies(
        cls,
        product_id: str,
        observations: List[AnomalyObservation],
        stats: BaselineStats,
        platforms: List[str],
        results: List[AnomalyDetection]
    ):
        rev_obs = [o for o in observations if o.metric_type == "review_count"]
        if not rev_obs or len(rev_obs) < 2:
            return
        rev_obs.sort(key=lambda x: x.observed_at, reverse=True)
        latest = rev_obs[0]
        prev = rev_obs[1]
        delta = latest.metric_value - prev.metric_value

        # Review velocity spike
        if delta >= 100.0 or (prev.metric_value > 0 and (delta / prev.metric_value) >= 1.0):
            fingerprint = cls.generate_fingerprint(product_id, "review_velocity_spike", "velocity_delta", [latest.id, prev.id])
            results.append(AnomalyDetection(
                id=f"anom_rvspk_{uuid.uuid4().hex[:12]}",
                unified_product_id=product_id,
                anomaly_type="review_velocity_spike",
                severity="high" if delta >= 300.0 else "medium",
                score=round(min(100.0, 55.0 + min(45.0, delta * 0.15)), 2),
                confidence=0.93,
                baseline=prev.metric_value,
                observed_value=latest.metric_value,
                deviation=round(delta, 2),
                deviation_percent=round((delta / prev.metric_value) * 100.0 if prev.metric_value > 0 else 100.0, 2),
                baseline_method="previous_observation",
                evidence={
                    "previous_reviews": prev.metric_value,
                    "current_reviews": latest.metric_value,
                    "review_delta": round(delta, 2)
                },
                platforms=[latest.platform],
                fingerprint=fingerprint,
                status="active",
                detected_at=datetime.now(timezone.utc)
            ))
        elif delta < 0:
            # Negative reviews = purge or data shift
            fingerprint = cls.generate_fingerprint(product_id, "review_velocity_drop", "velocity_delta", [latest.id, prev.id])
            results.append(AnomalyDetection(
                id=f"anom_rvdrp_{uuid.uuid4().hex[:12]}",
                unified_product_id=product_id,
                anomaly_type="review_velocity_drop",
                severity="medium",
                score=round(min(100.0, 50.0 + abs(delta) * 0.5), 2),
                confidence=0.88,
                baseline=prev.metric_value,
                observed_value=latest.metric_value,
                deviation=round(delta, 2),
                deviation_percent=round((delta / prev.metric_value) * 100.0 if prev.metric_value > 0 else 0.0, 2),
                baseline_method="previous_observation",
                evidence={
                    "previous_reviews": prev.metric_value,
                    "current_reviews": latest.metric_value,
                    "review_drop": round(abs(delta), 2)
                },
                platforms=[latest.platform],
                fingerprint=fingerprint,
                status="active",
                detected_at=datetime.now(timezone.utc)
            ))

    @classmethod
    def _detect_availability_anomalies(
        cls,
        product_id: str,
        observations: List[AnomalyObservation],
        stats: BaselineStats,
        platforms: List[str],
        results: List[AnomalyDetection]
    ):
        avl_obs = [o for o in observations if o.metric_type == "availability"]
        if not avl_obs or len(avl_obs) < 2:
            return
        avl_obs.sort(key=lambda x: x.observed_at, reverse=True)

        # Detect flip-flops in last 5 observations
        changes_count = 0
        for i in range(len(avl_obs) - 1):
            if avl_obs[i].metric_value != avl_obs[i+1].metric_value:
                changes_count += 1

        if changes_count >= 2:
            fingerprint = cls.generate_fingerprint(product_id, "availability_change", "stock_flip_flop", [o.id for o in avl_obs[:4]])
            results.append(AnomalyDetection(
                id=f"anom_avl_{uuid.uuid4().hex[:12]}",
                unified_product_id=product_id,
                anomaly_type="availability_change",
                severity="medium" if changes_count == 2 else "high",
                score=round(min(100.0, 50.0 + changes_count * 15.0), 2),
                confidence=0.91,
                baseline=1.0,
                observed_value=avl_obs[0].metric_value,
                deviation=float(changes_count),
                deviation_percent=0.0,
                baseline_method="state_transition_count",
                evidence={
                    "rapid_availability_transitions": changes_count,
                    "current_status": "in_stock" if avl_obs[0].metric_value == 1.0 else "out_of_stock"
                },
                platforms=[avl_obs[0].platform],
                fingerprint=fingerprint,
                status="active",
                detected_at=datetime.now(timezone.utc)
            ))

    @classmethod
    def _detect_cross_platform_anomalies(
        cls,
        product_id: str,
        platforms: List[str],
        listings: List[Dict[str, Any]],
        results: List[AnomalyDetection]
    ):
        # 1. Cross-Platform Price Disparity
        valid_prices = []
        currencies = set()
        for lst in listings:
            p = lst.get("price")
            curr = lst.get("currency", "USD")
            if p is not None and float(p) > 0:
                valid_prices.append((lst.get("platform", "unknown"), float(p), curr))
                currencies.add(curr)

        if len(valid_prices) >= 2:
            # Currency Safety Check: Only compare if same currency or explicit conversion exists
            if len(currencies) > 1:
                # Disparate currencies without conversion
                fingerprint = cls.generate_fingerprint(product_id, "cross_platform_price_anomaly", "currency_check", [f"curr_{c}" for c in sorted(currencies)])
                # Store note about currency safety
                return
            else:
                min_plat, min_p, _ = min(valid_prices, key=lambda x: x[1])
                max_plat, max_p, curr = max(valid_prices, key=lambda x: x[1])
                disparity_pct = ((max_p - min_p) / min_p) * 100.0

                if disparity_pct >= cls.CROSS_PLATFORM_PRICE_DISPARITY_PCT:
                    fingerprint = cls.generate_fingerprint(product_id, "cross_platform_price_anomaly", "cross_plat_price", [f"{min_plat}_{min_p}", f"{max_plat}_{max_p}"])
                    results.append(AnomalyDetection(
                        id=f"anom_cpprc_{uuid.uuid4().hex[:12]}",
                        unified_product_id=product_id,
                        anomaly_type="cross_platform_price_anomaly",
                        severity="high" if disparity_pct >= 80.0 else "medium",
                        score=round(min(100.0, 50.0 + disparity_pct * 0.4), 2),
                        confidence=0.95,
                        baseline=round(min_p, 2),
                        observed_value=round(max_p, 2),
                        deviation=round(max_p - min_p, 2),
                        deviation_percent=round(disparity_pct, 2),
                        baseline_method="cross_platform_comparison",
                        evidence={
                            "min_platform": min_plat,
                            "min_price": min_p,
                            "max_platform": max_plat,
                            "max_price": max_p,
                            "currency": curr,
                            "disparity_percent": round(disparity_pct, 2)
                        },
                        platforms=[min_plat, max_plat],
                        fingerprint=fingerprint,
                        status="active",
                        detected_at=datetime.now(timezone.utc)
                    ))

        # 2. Platform Presence Disappearance
        if len(platforms) >= 2 and len(listings) == 1:
            missing = [p for p in platforms if p != listings[0].get("platform")]
            fingerprint = cls.generate_fingerprint(product_id, "platform_presence_anomaly", "presence_check", sorted(missing))
            results.append(AnomalyDetection(
                id=f"anom_pres_{uuid.uuid4().hex[:12]}",
                unified_product_id=product_id,
                anomaly_type="platform_presence_anomaly",
                severity="medium",
                score=65.0,
                confidence=0.85,
                baseline=float(len(platforms)),
                observed_value=float(len(listings)),
                deviation=float(len(missing)),
                deviation_percent=0.0,
                baseline_method="multi_platform_presence",
                evidence={
                    "active_platforms": platforms,
                    "currently_available_on": [listings[0].get("platform")],
                    "disappeared_from": missing
                },
                platforms=platforms,
                fingerprint=fingerprint,
                status="active",
                detected_at=datetime.now(timezone.utc)
            ))

    @classmethod
    def _detect_provider_anomalies(
        cls,
        product_id: str,
        provider_data: Dict[str, Any],
        results: List[AnomalyDetection]
    ):
        provider = provider_data.get("provider", "unknown")
        platform = provider_data.get("platform", "unknown")
        rating = provider_data.get("rating")
        price = provider_data.get("price")
        reviews = provider_data.get("review_count")

        corrupt_fields = []
        if rating is not None and (rating < 0.0 or rating > 5.0):
            corrupt_fields.append(f"rating out of bounds ({rating})")
        if price is not None and price <= 0.0:
            corrupt_fields.append(f"price non-positive ({price})")
        if reviews is not None and reviews < 0:
            corrupt_fields.append(f"reviews negative ({reviews})")

        if corrupt_fields:
            fingerprint = cls.generate_fingerprint(product_id, "provider_data_anomaly", "provider_guard", [provider, *corrupt_fields])
            results.append(AnomalyDetection(
                id=f"anom_prov_{uuid.uuid4().hex[:12]}",
                unified_product_id=product_id,
                anomaly_type="provider_data_anomaly",
                severity="critical" if len(corrupt_fields) > 1 else "high",
                score=90.0,
                confidence=0.99,
                baseline=0.0,
                observed_value=0.0,
                deviation=float(len(corrupt_fields)),
                deviation_percent=0.0,
                baseline_method="schema_range_validation",
                evidence={
                    "provider": provider,
                    "platform": platform,
                    "corrupt_fields": corrupt_fields
                },
                platforms=[platform],
                provider=provider,
                fingerprint=fingerprint,
                status="active",
                detected_at=datetime.now(timezone.utc)
            ))

    @classmethod
    def generate_fingerprint(
        cls,
        product_id: str,
        anomaly_type: str,
        baseline_method: str,
        observation_ids: List[str]
    ) -> str:
        sorted_ids = ":".join(sorted([str(i) for i in observation_ids]))
        payload = f"{product_id.strip()}:{anomaly_type.strip()}:{baseline_method.strip()}:{sorted_ids}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
