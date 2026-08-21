from typing import List, Dict, Any, Tuple
import re
from backend.app.domain.signals import PlatformSignal

SPAM_PATTERNS = [
    r"free\s+money",
    r"crypto\s+giveaway",
    r"click\s+here\s+now",
    r"get\s+rich\s+quick",
    r"telegram\s*:\s*@",
    r"whatsapp\s*:\s*\+",
    r"100%\s+free\s+robux"
]

class DataQualityService:
    """
    Intelligence Agent: Inspects incoming external signals for schema anomalies,
    impossible metric values, negative counters, spam patterns, and calculates
    a calibrated 100-point Data Quality Score.
    """

    @staticmethod
    def calculate_normalized_rates(signal: PlatformSignal) -> Tuple[float, float, float]:
        """
        Calculates mathematically stable, non-zero-divided rates.
        Returns: (like_rate, comment_rate, engagement_rate)
        """
        denom = max(signal.views_count, signal.volume, 1)
        like_rate = round(min(max(signal.likes_count / denom, 0.0), 1.0), 4)
        comment_rate = round(min(max(signal.comments_count / denom, 0.0), 1.0), 4)
        
        # Standard combined engagement formula
        if signal.engagement_rate > 0:
            clamped_eng = round(min(max(signal.engagement_rate, 0.0), 1.0), 4)
        else:
            raw_eng = (signal.likes_count + (signal.comments_count * 2) + signal.shares_count) / denom
            clamped_eng = round(min(max(raw_eng, 0.0), 1.0), 4)
        
        return like_rate, comment_rate, clamped_eng

    @staticmethod
    def evaluate_quality(signal: PlatformSignal) -> Tuple[bool, float, List[str], List[str]]:
        """
        Calculates a 0-100 data quality score and identifies quality anomalies.
        Returns: (is_valid, quality_score, rejection_reasons, warnings)
        """
        score = 100.0
        reasons = []
        warnings = []
        flags = []

        # 1. Mandatory identifiers & title quality
        if not signal.platform or not signal.platform.strip():
            reasons.append("Missing platform identifier.")
            flags.append("MISSING_PLATFORM")
            score -= 40.0

        if not signal.product_name or not signal.product_name.strip():
            reasons.append("Missing product/content title.")
            flags.append("MISSING_TITLE")
            score -= 40.0
        elif len(signal.product_name.strip()) < 3:
            warnings.append("Suspiciously short title (<3 chars).")
            flags.append("SHORT_TITLE")
            score -= 15.0

        # 2. Volume & view counts bounds
        if signal.volume < 0:
            reasons.append(f"Volume cannot be negative (got {signal.volume}).")
            flags.append("NEGATIVE_VOLUME")
            score -= 50.0

        if signal.views_count < 0:
            reasons.append(f"Views count cannot be negative (got {signal.views_count}).")
            flags.append("NEGATIVE_VIEWS")
            score -= 50.0

        # 3. Likes, comments, and shares non-negative check
        if signal.likes_count < 0 or signal.comments_count < 0 or signal.shares_count < 0:
            reasons.append("Likes, comments, or shares cannot be negative.")
            flags.append("NEGATIVE_COUNTERS")
            score -= 50.0

        # 4. Metric consistency (e.g. likes > views when views > 0)
        if signal.views_count > 0 and signal.likes_count > signal.views_count:
            warnings.append("Likes count exceeds views count.")
            flags.append("LIKES_EXCEED_VIEWS")
            score -= 20.0

        # 5. Spam detection
        title_lower = signal.product_name.lower()
        for pattern in SPAM_PATTERNS:
            if re.search(pattern, title_lower):
                warnings.append("Potential spam/clickbait pattern detected.")
                flags.append("SPAM_PATTERN_DETECTED")
                score -= 25.0
                break

        # 6. Normalize rates and update signal
        if signal.engagement_rate > 1.0 or signal.engagement_rate < 0.0:
            warnings.append(f"Engagement rate {signal.engagement_rate} clamped to [0.0, 1.0].")
            flags.append("ENGAGEMENT_CLAMPED")

        like_rate, comment_rate, eng_rate = DataQualityService.calculate_normalized_rates(signal)
        signal.like_rate = like_rate
        signal.comment_rate = comment_rate
        signal.engagement_rate = eng_rate

        # 7. Sentiment sanity
        if signal.sentiment_score < 0.0 or signal.sentiment_score > 1.0:
            warnings.append(f"Sentiment score {signal.sentiment_score} clamped to [0.0, 1.0].")
            signal.sentiment_score = min(max(signal.sentiment_score, 0.0), 1.0)
            flags.append("SENTIMENT_CLAMPED")
            score -= 5.0

        final_quality_score = round(min(max(score, 0.0), 100.0), 1)
        signal.data_quality_score = final_quality_score
        signal.quality_flags = flags

        # A signal is valid if there are no hard rejection reasons and quality score >= 35
        is_valid = (len(reasons) == 0) and (final_quality_score >= 35.0)

        return is_valid, final_quality_score, reasons, warnings

    @staticmethod
    def validate_signal(signal: PlatformSignal) -> Tuple[bool, List[str], List[str]]:
        """Backward-compatible validation wrapper."""
        is_valid, _, reasons, warnings = DataQualityService.evaluate_quality(signal)
        return is_valid, reasons, warnings
