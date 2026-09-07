import hashlib
import uuid
import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from backend.app.models.domain import TrendObservation, TrendSignal, TrendSignalCandidate

class TrendSignalRulesEngine:
    """
    Deterministic rule-based signal detection engine.
    Processes historical metric observations to extract grounded product and market signals.
    """

    @staticmethod
    def generate_fingerprint(
        unified_product_id: str,
        signal_type: str,
        direction: str,
        observation_ids: List[str]
    ) -> str:
        """
        Creates a deterministic hash fingerprint from product ID, signal type, direction,
        and sorted input observation IDs to prevent duplicate signals.
        """
        sorted_ids = sorted(observation_ids)
        raw_key = f"{unified_product_id}:{signal_type}:{direction}:{','.join(sorted_ids)}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def evaluate_all_signals(
        cls,
        unified_product_id: str,
        observations: List[TrendObservation],
        active_platforms: List[str]
    ) -> List[TrendSignal]:
        """
        Evaluates observations for all 10 signal categories deterministically.
        Returns a list of grounded TrendSignal instances.
        """
        if not observations or len(observations) < 1:
            return []

        signals: List[TrendSignal] = []

        # 1. Price Movement & Discounts
        price_signals = cls._detect_price_signals(unified_product_id, observations)
        signals.extend(price_signals)

        # 2. Review Momentum & Growth
        review_signals = cls._detect_review_signals(unified_product_id, observations)
        signals.extend(review_signals)

        # 3. Rating Momentum
        rating_signals = cls._detect_rating_signals(unified_product_id, observations)
        signals.extend(rating_signals)

        # 4. Inventory & Availability
        inventory_signals = cls._detect_inventory_signals(unified_product_id, observations)
        signals.extend(inventory_signals)

        # 5. Demand Surge (Synthesizing review velocity + availability/price signals)
        demand_signals = cls._detect_demand_surge(unified_product_id, observations, review_signals)
        signals.extend(demand_signals)

        # 6. Cross-Platform Surge
        cross_signals = cls._detect_cross_platform_surge(unified_product_id, observations, active_platforms)
        signals.extend(cross_signals)

        # 7. Emerging & Declining Product Signals
        lifecycle_signals = cls._detect_lifecycle_signals(unified_product_id, observations)
        signals.extend(lifecycle_signals)

        # 8. Unusual Market Activity
        unusual_signals = cls._detect_unusual_activity(unified_product_id, observations)
        signals.extend(unusual_signals)

        return signals

    # ------------------------------------------------------------------------
    # SPECIFIC DETERMINISTIC DETECTORS
    # ------------------------------------------------------------------------

    @classmethod
    def _detect_price_signals(
        cls,
        unified_product_id: str,
        observations: List[TrendObservation]
    ) -> List[TrendSignal]:
        signals = []
        price_obs = [o for o in observations if o.metric_type == "price"]
        if len(price_obs) < 2:
            return signals

        # Sort by observation time ascending to track trajectory
        sorted_p = sorted(price_obs, key=lambda o: o.observed_at)
        latest = sorted_p[-1]
        prev = sorted_p[-2]

        if latest.previous_value is not None and prev.metric_value > 0:
            chg_pct = latest.change_percent or round(((latest.metric_value - prev.metric_value) / prev.metric_value) * 100, 2)
            obs_ids = [prev.id, latest.id]
            curr_code = latest.metadata.get("currency", "PKR")

            # Price Drop
            if chg_pct <= -5.0:
                is_large = chg_pct <= -20.0
                sig_type = "large_discount" if is_large else "price_drop"
                strength = min(100.0, abs(chg_pct) * 2.0)
                severity = "high" if is_large else "medium"
                fp = cls.generate_fingerprint(unified_product_id, sig_type, "down", obs_ids)

                signals.append(TrendSignal(
                    id=f"sig_{uuid.uuid4().hex[:12]}",
                    unified_product_id=unified_product_id,
                    signal_type=sig_type,
                    signal_strength=round(strength, 1),
                    confidence=0.95,
                    direction="down",
                    severity=severity,
                    status="active",
                    evidence={
                        "previous_price": prev.metric_value,
                        "current_price": latest.metric_value,
                        "change_percent": chg_pct,
                        "currency": curr_code,
                        "platform": latest.platform,
                        "observed_at": latest.observed_at.isoformat()
                    },
                    platforms=[latest.platform],
                    fingerprint=fp,
                    detected_at=latest.observed_at
                ))

            # Price Increase
            elif chg_pct >= 5.0:
                strength = min(100.0, chg_pct * 1.8)
                fp = cls.generate_fingerprint(unified_product_id, "price_increase", "up", obs_ids)
                signals.append(TrendSignal(
                    id=f"sig_{uuid.uuid4().hex[:12]}",
                    unified_product_id=unified_product_id,
                    signal_type="price_increase",
                    signal_strength=round(strength, 1),
                    confidence=0.95,
                    direction="up",
                    severity="medium",
                    status="active",
                    evidence={
                        "previous_price": prev.metric_value,
                        "current_price": latest.metric_value,
                        "change_percent": chg_pct,
                        "currency": curr_code,
                        "platform": latest.platform,
                        "observed_at": latest.observed_at.isoformat()
                    },
                    platforms=[latest.platform],
                    fingerprint=fp,
                    detected_at=latest.observed_at
                ))

            # Price Stability
            elif abs(chg_pct) < 1.0 and len(sorted_p) >= 3:
                fp = cls.generate_fingerprint(unified_product_id, "price_stable", "stable", obs_ids)
                signals.append(TrendSignal(
                    id=f"sig_{uuid.uuid4().hex[:12]}",
                    unified_product_id=unified_product_id,
                    signal_type="price_movement",
                    signal_strength=50.0,
                    confidence=0.92,
                    direction="stable",
                    severity="low",
                    status="active",
                    evidence={
                        "current_price": latest.metric_value,
                        "change_percent": chg_pct,
                        "stability_window_observations": len(sorted_p),
                        "platform": latest.platform
                    },
                    platforms=[latest.platform],
                    fingerprint=fp,
                    detected_at=latest.observed_at
                ))

        # Price Volatility (3+ observations with alternating directions)
        if len(sorted_p) >= 3:
            prices = [o.metric_value for o in sorted_p[-5:]]
            mean_p = sum(prices) / len(prices)
            variance = sum((p - mean_p) ** 2 for p in prices) / len(prices)
            std_dev = math.sqrt(variance)
            cv = (std_dev / mean_p) if mean_p > 0 else 0.0

            if cv >= 0.15:  # >= 15% coefficient of variation
                obs_ids = [o.id for o in sorted_p[-5:]]
                fp = cls.generate_fingerprint(unified_product_id, "price_volatility", "volatile", obs_ids)
                signals.append(TrendSignal(
                    id=f"sig_{uuid.uuid4().hex[:12]}",
                    unified_product_id=unified_product_id,
                    signal_type="price_volatility",
                    signal_strength=min(100.0, round(cv * 300.0, 1)),
                    confidence=0.90,
                    direction="volatile",
                    severity="high",
                    status="active",
                    evidence={
                        "coefficient_of_variation": round(cv, 3),
                        "price_history": prices,
                        "observation_count": len(prices)
                    },
                    platforms=list(set(o.platform for o in sorted_p[-5:])),
                    fingerprint=fp,
                    detected_at=sorted_p[-1].observed_at
                ))

        return signals

    @classmethod
    def _detect_review_signals(
        cls,
        unified_product_id: str,
        observations: List[TrendObservation]
    ) -> List[TrendSignal]:
        signals = []
        rev_obs = [o for o in observations if o.metric_type == "review_count"]
        if len(rev_obs) < 2:
            return signals

        sorted_r = sorted(rev_obs, key=lambda o: o.observed_at)
        latest = sorted_r[-1]
        prev = sorted_r[-2]

        if latest.previous_value is not None:
            prev_val = prev.metric_value
            curr_val = latest.metric_value
            chg_val = curr_val - prev_val
            chg_pct = round(((curr_val - prev_val) / prev_val) * 100, 2) if prev_val > 0 else (100.0 if curr_val > 0 else 0.0)
            obs_ids = [prev.id, latest.id]

            if chg_val > 0 and chg_pct >= 10.0:
                strength = min(100.0, round(chg_pct * 1.5, 1))
                severity = "high" if chg_pct >= 30.0 else "medium"
                fp = cls.generate_fingerprint(unified_product_id, "review_momentum", "up", obs_ids)
                signals.append(TrendSignal(
                    id=f"sig_{uuid.uuid4().hex[:12]}",
                    unified_product_id=unified_product_id,
                    signal_type="review_momentum",
                    signal_strength=strength,
                    confidence=0.94,
                    direction="up",
                    severity=severity,
                    status="active",
                    evidence={
                        "previous_count": prev_val,
                        "current_count": curr_val,
                        "change_count": chg_val,
                        "growth_percent": chg_pct,
                        "platform": latest.platform,
                        "observed_at": latest.observed_at.isoformat()
                    },
                    platforms=[latest.platform],
                    fingerprint=fp,
                    detected_at=latest.observed_at
                ))
            elif chg_val < 0:
                fp = cls.generate_fingerprint(unified_product_id, "review_decline", "down", obs_ids)
                signals.append(TrendSignal(
                    id=f"sig_{uuid.uuid4().hex[:12]}",
                    unified_product_id=unified_product_id,
                    signal_type="review_momentum",
                    signal_strength=40.0,
                    confidence=0.85,
                    direction="down",
                    severity="low",
                    status="active",
                    evidence={
                        "previous_count": prev_val,
                        "current_count": curr_val,
                        "change_count": chg_val,
                        "growth_percent": chg_pct,
                        "platform": latest.platform
                    },
                    platforms=[latest.platform],
                    fingerprint=fp,
                    detected_at=latest.observed_at
                ))

        return signals

    @classmethod
    def _detect_rating_signals(
        cls,
        unified_product_id: str,
        observations: List[TrendObservation]
    ) -> List[TrendSignal]:
        signals = []
        rtg_obs = [o for o in observations if o.metric_type == "rating"]
        if len(rtg_obs) < 2:
            return signals

        sorted_rtg = sorted(rtg_obs, key=lambda o: o.observed_at)
        latest = sorted_rtg[-1]
        prev = sorted_rtg[-2]

        if latest.previous_value is not None:
            delta = round(latest.metric_value - prev.metric_value, 2)
            obs_ids = [prev.id, latest.id]

            if delta >= 0.2:
                fp = cls.generate_fingerprint(unified_product_id, "rating_momentum", "up", obs_ids)
                signals.append(TrendSignal(
                    id=f"sig_{uuid.uuid4().hex[:12]}",
                    unified_product_id=unified_product_id,
                    signal_type="rating_momentum",
                    signal_strength=min(100.0, round(delta * 100.0, 1)),
                    confidence=0.92,
                    direction="up",
                    severity="medium",
                    status="active",
                    evidence={
                        "previous_rating": prev.metric_value,
                        "current_rating": latest.metric_value,
                        "rating_delta": delta,
                        "platform": latest.platform
                    },
                    platforms=[latest.platform],
                    fingerprint=fp,
                    detected_at=latest.observed_at
                ))
            elif delta <= -0.2:
                fp = cls.generate_fingerprint(unified_product_id, "rating_momentum", "down", obs_ids)
                signals.append(TrendSignal(
                    id=f"sig_{uuid.uuid4().hex[:12]}",
                    unified_product_id=unified_product_id,
                    signal_type="rating_momentum",
                    signal_strength=min(100.0, round(abs(delta) * 100.0, 1)),
                    confidence=0.92,
                    direction="down",
                    severity="high",
                    status="active",
                    evidence={
                        "previous_rating": prev.metric_value,
                        "current_rating": latest.metric_value,
                        "rating_delta": delta,
                        "platform": latest.platform
                    },
                    platforms=[latest.platform],
                    fingerprint=fp,
                    detected_at=latest.observed_at
                ))

        return signals

    @classmethod
    def _detect_inventory_signals(
        cls,
        unified_product_id: str,
        observations: List[TrendObservation]
    ) -> List[TrendSignal]:
        signals = []
        avail_obs = [o for o in observations if o.metric_type == "availability"]
        if len(avail_obs) < 2:
            return signals

        sorted_a = sorted(avail_obs, key=lambda o: o.observed_at)
        latest = sorted_a[-1]
        prev = sorted_a[-2]

        obs_ids = [prev.id, latest.id]

        # In stock -> Out of stock
        if prev.metric_value == 1.0 and latest.metric_value == 0.0:
            fp = cls.generate_fingerprint(unified_product_id, "out_of_stock", "down", obs_ids)
            signals.append(TrendSignal(
                id=f"sig_{uuid.uuid4().hex[:12]}",
                unified_product_id=unified_product_id,
                signal_type="out_of_stock",
                signal_strength=80.0,
                confidence=0.98,
                direction="down",
                severity="high",
                status="active",
                evidence={
                    "previous_status": "in_stock",
                    "current_status": "out_of_stock",
                    "platform": latest.platform,
                    "observed_at": latest.observed_at.isoformat()
                },
                platforms=[latest.platform],
                fingerprint=fp,
                detected_at=latest.observed_at
            ))

        # Out of stock -> Restocked
        elif prev.metric_value == 0.0 and latest.metric_value == 1.0:
            fp = cls.generate_fingerprint(unified_product_id, "restocked", "up", obs_ids)
            signals.append(TrendSignal(
                id=f"sig_{uuid.uuid4().hex[:12]}",
                unified_product_id=unified_product_id,
                signal_type="restocked",
                signal_strength=75.0,
                confidence=0.98,
                direction="up",
                severity="medium",
                status="active",
                evidence={
                    "previous_status": "out_of_stock",
                    "current_status": "restocked",
                    "platform": latest.platform,
                    "observed_at": latest.observed_at.isoformat()
                },
                platforms=[latest.platform],
                fingerprint=fp,
                detected_at=latest.observed_at
            ))

        return signals

    @classmethod
    def _detect_demand_surge(
        cls,
        unified_product_id: str,
        observations: List[TrendObservation],
        review_signals: List[TrendSignal]
    ) -> List[TrendSignal]:
        signals = []
        strong_rev_surge = [s for s in review_signals if s.direction == "up" and s.evidence.get("growth_percent", 0) >= 20.0]
        if strong_rev_surge:
            lead = strong_rev_surge[0]
            obs_ids = [o.id for o in observations[-4:]]
            fp = cls.generate_fingerprint(unified_product_id, "demand_surge", "up", obs_ids)
            signals.append(TrendSignal(
                id=f"sig_{uuid.uuid4().hex[:12]}",
                unified_product_id=unified_product_id,
                signal_type="demand_surge",
                signal_strength=lead.signal_strength,
                confidence=0.91,
                direction="up",
                severity="high",
                status="active",
                evidence={
                    "basis": "Verified review velocity acceleration",
                    "review_growth_percent": lead.evidence.get("growth_percent"),
                    "platform": lead.evidence.get("platform")
                },
                platforms=lead.platforms,
                fingerprint=fp,
                detected_at=lead.detected_at
            ))
        return signals

    @classmethod
    def _detect_cross_platform_surge(
        cls,
        unified_product_id: str,
        observations: List[TrendObservation],
        active_platforms: List[str]
    ) -> List[TrendSignal]:
        signals = []
        if len(active_platforms) < 2:
            return signals

        # Check if 2 or more platforms have recent positive momentum
        platforms_with_activity = set()
        for obs in observations:
            if obs.platform in active_platforms and obs.metric_type in ["price", "review_count", "rating"]:
                platforms_with_activity.add(obs.platform)

        if len(platforms_with_activity) >= 2:
            obs_ids = [o.id for o in observations[-6:]]
            fp = cls.generate_fingerprint(unified_product_id, "cross_platform_surge", "up", obs_ids)
            signals.append(TrendSignal(
                id=f"sig_{uuid.uuid4().hex[:12]}",
                unified_product_id=unified_product_id,
                signal_type="cross_platform_surge",
                signal_strength=min(100.0, 60.0 + (len(platforms_with_activity) * 15.0)),
                confidence=0.93,
                direction="up",
                severity="high",
                status="active",
                evidence={
                    "active_platform_count": len(platforms_with_activity),
                    "active_platforms": list(platforms_with_activity),
                    "observation_count": len(observations)
                },
                platforms=list(platforms_with_activity),
                fingerprint=fp,
                detected_at=datetime.now(timezone.utc)
            ))

        return signals

    @classmethod
    def _detect_lifecycle_signals(
        cls,
        unified_product_id: str,
        observations: List[TrendObservation]
    ) -> List[TrendSignal]:
        signals = []
        now = datetime.now(timezone.utc)
        earliest_obs = min(observations, key=lambda o: o.observed_at)
        age = now - earliest_obs.observed_at

        # Emerging: Product first observed < 30 days ago with >= 2 positive observations
        if age <= timedelta(days=30) and len(observations) >= 2:
            obs_ids = [earliest_obs.id, observations[-1].id]
            fp = cls.generate_fingerprint(unified_product_id, "emerging_product", "up", obs_ids)
            signals.append(TrendSignal(
                id=f"sig_{uuid.uuid4().hex[:12]}",
                unified_product_id=unified_product_id,
                signal_type="emerging_product",
                signal_strength=70.0,
                confidence=0.88,
                direction="up",
                severity="medium",
                status="active",
                evidence={
                    "first_observed_age_days": round(age.total_seconds() / 86400, 1),
                    "total_observations": len(observations)
                },
                platforms=list(set(o.platform for o in observations)),
                fingerprint=fp,
                detected_at=now
            ))

        return signals

    @classmethod
    def _detect_unusual_activity(
        cls,
        unified_product_id: str,
        observations: List[TrendObservation]
    ) -> List[TrendSignal]:
        signals = []
        # Check for extreme sudden swings (> 50% price change in single observation)
        for obs in observations:
            if obs.metric_type == "price" and obs.change_percent and abs(obs.change_percent) >= 50.0:
                fp = cls.generate_fingerprint(unified_product_id, "unusual_activity", "volatile", [obs.id])
                signals.append(TrendSignal(
                    id=f"sig_{uuid.uuid4().hex[:12]}",
                    unified_product_id=unified_product_id,
                    signal_type="unusual_activity",
                    signal_strength=90.0,
                    confidence=0.96,
                    direction="volatile",
                    severity="critical",
                    status="active",
                    evidence={
                        "extreme_metric": "price",
                        "change_percent": obs.change_percent,
                        "previous_value": obs.previous_value,
                        "current_value": obs.metric_value,
                        "platform": obs.platform
                    },
                    platforms=[obs.platform],
                    fingerprint=fp,
                    detected_at=obs.observed_at
                ))
                break

        return signals
