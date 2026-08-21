from typing import List, Dict, Any

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
