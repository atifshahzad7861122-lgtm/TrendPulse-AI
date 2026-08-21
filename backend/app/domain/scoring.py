from typing import List, Dict, Any, Optional, Tuple
import math

class TrendScoreDetail:
    def __init__(
        self,
        trend_score: float,
        growth_component: float,
        velocity_component: float,
        momentum_component: float,
        volume_component: float,
        engagement_component: float,
        dispersion_component: float,
        top_contributors: List[str],
        velocity_label: str,
        scoring_version: str = "2.4.0"
    ):
        self.trend_score = trend_score
        self.growth_component = growth_component
        self.velocity_component = velocity_component
        self.momentum_component = momentum_component
        self.volume_component = volume_component
        self.engagement_component = engagement_component
        self.dispersion_component = dispersion_component
        self.top_contributors = top_contributors
        self.velocity_label = velocity_label
        self.scoring_version = scoring_version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trend_score": self.trend_score,
            "growth_component": self.growth_component,
            "velocity_component": self.velocity_component,
            "momentum_component": self.momentum_component,
            "volume_component": self.volume_component,
            "engagement_component": self.engagement_component,
            "dispersion_component": self.dispersion_component,
            "top_contributors": self.top_contributors,
            "velocity_label": self.velocity_label,
            "scoring_version": self.scoring_version
        }

class TrendScoringEngine:
    """
    Deterministic mathematical engine for calculating Velocity, Growth,
    Momentum, and Explainable Composite Trend Scores.
    """

    SCORING_VERSION = "2.4.0"

    @staticmethod
    def calculate_growth_rate(current_volume: float, baseline_volume: float) -> float:
        """
        Calculates percentage growth rate relative to baseline.
        Formula: G = ((V_t - V_0) / V_0) * 100
        """
        if baseline_volume <= 0:
            return 0.0 if current_volume <= 0 else 100.0
        growth = ((current_volume - baseline_volume) / baseline_volume) * 100.0
        return round(growth, 1)

    @staticmethod
    def calculate_velocity(historical_volumes: List[float], days_delta: float = 7.0) -> float:
        """
        Calculates average daily change in volume.
        Formula: V = (V_end - V_start) / days_delta
        """
        if not historical_volumes or len(historical_volumes) < 2:
            return 0.0
        start = historical_volumes[0]
        end = historical_volumes[-1]
        dt = max(days_delta, 1.0)
        return round((end - start) / dt, 2)

    @staticmethod
    def calculate_momentum(historical_scores: List[float]) -> float:
        """
        Calculates acceleration/momentum of the score.
        Formula: M = (Recent delta) - (Previous delta)
        """
        if not historical_scores or len(historical_scores) < 3:
            return 0.0
        recent_delta = historical_scores[-1] - historical_scores[-2]
        prev_delta = historical_scores[-2] - historical_scores[-3]
        return round(recent_delta - prev_delta, 2)

    @staticmethod
    def calculate_explainable_trend_score(
        growth_rate: float,
        volume: int,
        sentiment_score: float,
        platform_count: int,
        engagement_rate: float = 0.08,
        historical_trend: Optional[List[float]] = None
    ) -> TrendScoreDetail:
        """
        Calculates a calibrated composite trend score with full explainability.
        Weights:
        - 35% Normalized Growth (growth / 350.0 capped at 1.0)
        - 25% Normalized Volume (log10(volume) / 6.0 capped at 1.0)
        - 20% Sentiment Score (0.0 to 1.0)
        - 20% Platform Dispersion (min(platform_count / 4.0, 1.0))
        """
        # 1. Growth factor (35%)
        norm_growth = min(max(growth_rate / 350.0, 0.0), 1.0)
        growth_pts = round(norm_growth * 35.0, 1)

        # 2. Volume factor (25%)
        vol = max(volume, 100)
        norm_volume = min(max((math.log10(vol) - 2.0) / 4.0, 0.0), 1.0)
        volume_pts = round(norm_volume * 25.0, 1)

        # 3. Sentiment factor (20%)
        norm_sentiment = min(max(sentiment_score, 0.0), 1.0)
        sentiment_pts = round(norm_sentiment * 20.0, 1)

        # 4. Platform dispersion factor (20%)
        norm_dispersion = min(max(platform_count / 4.0, 0.25), 1.0)
        dispersion_pts = round(norm_dispersion * 20.0, 1)

        # 5. Engagement & Momentum adjustments
        engagement_pts = round(min(engagement_rate * 50.0, 5.0), 1)
        momentum_pts = 0.0
        if historical_trend and len(historical_trend) >= 2:
            if historical_trend[-1] > historical_trend[-2]:
                momentum_pts = 2.0

        raw_score = growth_pts + volume_pts + sentiment_pts + dispersion_pts + momentum_pts
        final_score = round(min(max(raw_score, 10.0), 99.5), 1)

        # Determine velocity label
        vel_label = TrendScoringEngine.get_velocity_label(final_score, growth_rate)

        # Identify top contributors
        contributors = []
        if growth_rate >= 200.0:
            contributors.append(f"High growth velocity (+{growth_rate:.0f}%)")
        if volume >= 100000:
            contributors.append(f"Strong market volume ({volume:,})")
        if sentiment_score >= 0.85:
            contributors.append("Exceptional positive audience sentiment")
        if platform_count >= 3:
            contributors.append(f"Cross-channel dispersion ({platform_count} platforms)")
        if engagement_rate >= 0.08:
            contributors.append(f"High engagement rate ({engagement_rate * 100:.1f}%)")
        if not contributors:
            contributors.append("Baseline organic signal activity")

        return TrendScoreDetail(
            trend_score=final_score,
            growth_component=growth_pts,
            velocity_component=round(growth_pts * 0.6, 1),
            momentum_component=momentum_pts,
            volume_component=volume_pts,
            engagement_component=engagement_pts,
            dispersion_component=dispersion_pts,
            top_contributors=contributors[:3],
            velocity_label=vel_label,
            scoring_version=TrendScoringEngine.SCORING_VERSION
        )

    @staticmethod
    def calculate_trend_score(
        growth_rate: float,
        volume: int,
        sentiment_score: float,
        platform_count: int,
        historical_trend: Optional[List[float]] = None
    ) -> float:
        """Backward-compatible wrapper returning float score."""
        detail = TrendScoringEngine.calculate_explainable_trend_score(
            growth_rate=growth_rate,
            volume=volume,
            sentiment_score=sentiment_score,
            platform_count=platform_count,
            historical_trend=historical_trend
        )
        return detail.trend_score

    @staticmethod
    def get_velocity_label(score: float, growth: float) -> str:
        """Categorize velocity into human-readable strategic labels."""
        if score >= 95.0 or growth >= 300.0:
            return "Explosive"
        elif score >= 90.0 or growth >= 180.0:
            return "Breakout"
        elif score >= 80.0 or growth >= 80.0:
            return "Surging"
        else:
            return "Steady"
