from typing import List, Dict, Any, Optional

class ViralEvaluationResult:
    def __init__(
        self,
        label: str,
        viral_score: float,
        confidence: int,
        contributors: List[str],
        engine_version: str = "2.4.0"
    ):
        self.label = label
        self.viral_score = viral_score
        self.confidence = confidence
        self.contributors = contributors
        self.engine_version = engine_version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "viral_score": self.viral_score,
            "confidence": self.confidence,
            "contributors": self.contributors,
            "engine_version": self.engine_version
        }

class ViralPotentialEngine:
    """
    Evaluates multi-channel virality, cross-platform spread,
    and velocity acceleration to classify viral potential and explainability.
    """

    ENGINE_VERSION = "2.4.0"

    @staticmethod
    def evaluate_virality_detailed(
        growth_rate: float,
        platforms: List[str],
        platform_shares: Dict[str, float],
        velocity_label: str
    ) -> ViralEvaluationResult:
        has_tiktok = "TikTok" in platforms
        has_instagram = "Instagram" in platforms
        has_youtube = "YouTube" in platforms
        tiktok_share = platform_shares.get("TikTok", 0.0)
        
        viral_score = 0.0
        contributors = []

        if growth_rate >= 250.0:
            viral_score += 40.0
            contributors.append(f"Parabolic growth acceleration (+{growth_rate:.0f}%)")
        elif growth_rate >= 150.0:
            viral_score += 25.0
            contributors.append(f"Strong viral velocity (+{growth_rate:.0f}%)")
        elif growth_rate >= 80.0:
            viral_score += 15.0
            contributors.append(f"Healthy growth momentum (+{growth_rate:.0f}%)")

        if has_tiktok and tiktok_share >= 40.0:
            viral_score += 30.0
            contributors.append(f"Heavy TikTok saturation ({tiktok_share:.0f}% share)")
        elif has_tiktok:
            viral_score += 15.0
            contributors.append("TikTok creator activity detected")

        if has_instagram:
            viral_score += 15.0
            contributors.append("Instagram visual lifestyle resonance")

        if has_youtube:
            viral_score += 10.0
            contributors.append("YouTube long-form review amplification")

        if len(platforms) >= 3:
            viral_score += 15.0
            contributors.append(f"Omni-channel spread across {len(platforms)} platforms")

        if velocity_label == "Explosive":
            viral_score += 15.0
        elif velocity_label == "Breakout":
            viral_score += 10.0

        clamped_score = round(min(max(viral_score, 10.0), 99.0), 1)

        if clamped_score >= 80.0:
            label = "Very High"
        elif clamped_score >= 55.0:
            label = "High"
        elif clamped_score >= 35.0:
            label = "Moderate"
        else:
            label = "Low"

        # Calculate confidence based on platform diversity and velocity clarity
        confidence = int(min(65 + (len(platforms) * 8) + (20 if has_tiktok else 0), 95))

        if not contributors:
            contributors.append("Baseline social awareness")

        return ViralEvaluationResult(
            label=label,
            viral_score=clamped_score,
            confidence=confidence,
            contributors=contributors[:3],
            engine_version=ViralPotentialEngine.ENGINE_VERSION
        )

    @staticmethod
    def calculate_viral_potential(
        growth_rate: float,
        platforms: List[str],
        platform_shares: Dict[str, float],
        velocity_label: str
    ) -> str:
        """Backward-compatible wrapper returning string label."""
        res = ViralPotentialEngine.evaluate_virality_detailed(
            growth_rate, platforms, platform_shares, velocity_label
        )
        return res.label

    @staticmethod
    def evaluate_from_social_signals(
        signals: List[Any],  # List[SocialSignal] or list of signal dicts
        growth_rate: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Evaluates virality strictly when verified social signals exist.
        Returns unavailable when no social signals are present.
        """
        if not signals or len(signals) == 0:
            return {
                "viral_score": None,
                "viral_level": "unavailable",
                "confidence": 0.0,
                "has_social_signals": False,
                "supporting_signals": []
            }

        total_views = 0
        total_likes = 0
        total_comments = 0
        total_shares = 0
        platforms = set()

        for s in signals:
            if hasattr(s, "views"):
                views = getattr(s, "views", 0) or 0
                likes = getattr(s, "likes", 0) or 0
                comments = getattr(s, "comments", 0) or 0
                shares = getattr(s, "shares", 0) or 0
                plat = getattr(s, "platform", "")
            elif isinstance(s, dict):
                views = s.get("views", 0) or 0
                likes = s.get("likes", 0) or 0
                comments = s.get("comments", 0) or 0
                shares = s.get("shares", 0) or 0
                plat = s.get("platform", "")
            else:
                continue

            total_views += views
            total_likes += likes
            total_comments += comments
            total_shares += shares
            if plat:
                platforms.add(plat)

        if total_views == 0 and total_likes == 0 and len(signals) == 0:
            return {
                "viral_score": None,
                "viral_level": "unavailable",
                "confidence": 0.0,
                "has_social_signals": False,
                "supporting_signals": []
            }

        score = 0.0
        contributors = []

        # View volume (log scale, up to 40 pts)
        if total_views >= 500000:
            score += 40.0
            contributors.append(f"Viral reach: {total_views:,} verified video views")
        elif total_views >= 200000:
            score += 35.0
            contributors.append(f"Massive social visibility ({total_views:,} views)")
        elif total_views >= 100000:
            score += 30.0
            contributors.append(f"Significant social visibility ({total_views:,} views)")
        elif total_views >= 10000:
            score += 20.0
            contributors.append(f"Growing video exposure ({total_views:,} views)")
        elif total_views > 0:
            score += 10.0

        # Engagement: Likes + Comments + Shares (up to 30 pts)
        eng_total = total_likes + total_comments + total_shares
        if eng_total >= 25000:
            score += 30.0
            contributors.append(f"High social engagement: {eng_total:,} interactions")
        elif eng_total >= 10000:
            score += 25.0
            contributors.append(f"Strong social engagement ({eng_total:,} interactions)")
        elif eng_total >= 5000:
            score += 20.0
            contributors.append(f"Active audience discussions ({eng_total:,} interactions)")
        elif eng_total >= 500:
            score += 10.0

        # Platform Diversity (up to 15 pts)
        if len(platforms) >= 3:
            score += 15.0
            contributors.append(f"Multi-network presence across {', '.join(platforms)}")
        elif len(platforms) == 2:
            score += 10.0
            contributors.append(f"Cross-channel spread on {', '.join(platforms)}")
        elif len(platforms) == 1:
            score += 5.0

        # Growth bonus (up to 15 pts)
        if growth_rate and growth_rate > 50.0:
            score += 15.0
            contributors.append(f"Accelerating social interest (+{growth_rate:.0f}%)")

        clamped = round(min(max(score, 5.0), 99.0), 1)

        if clamped >= 80.0:
            level = "Very High"
        elif clamped >= 60.0:
            level = "High"
        elif clamped >= 35.0:
            level = "Moderate"
        else:
            level = "Low"

        conf = min(0.40 + (min(total_views / 200000.0, 1.0) * 0.35) + (len(platforms) * 0.10), 0.95)

        return {
            "viral_score": clamped,
            "viral_level": level,
            "confidence": round(conf, 2),
            "has_social_signals": True,
            "supporting_signals": contributors
        }
