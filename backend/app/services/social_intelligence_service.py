"""
Phase 3 Social Platform Intelligence Service.

Extracts, aggregates, and matches real social signals from supported social networks
(YouTube, public social feeds) to marketplace products using deterministic confidence-gated matching.
Never fabricates social views, likes, shares, or engagement.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from backend.app.models.domain import SocialSignal, Product, UnifiedProduct, MarketplaceProduct
from backend.app.schemas.market_intelligence import SocialSignalItem, SocialIntelligenceResponse
from backend.app.domain.matching import ProductMatchingEngine
from backend.app.domain.viral import ViralPotentialEngine
from backend.app.connectors.youtube_connector import YouTubeDataConnector
from backend.app.connectors.social_platform_connector import MultiPlatformSocialConnector
from backend.app.repositories.base import MarketIntelligenceRepository
from backend.app.repositories.in_memory import market_intelligence_repo

logger = logging.getLogger("trendpulse.social_intelligence")


class SocialIntelligenceService:
    """
    Coordinates multi-platform social demand extraction across YouTube, X/Twitter,
    TikTok, Instagram, and Facebook, with deterministic product matching and persistence.
    """

    MATCH_CONFIDENCE_THRESHOLD = 0.75

    def __init__(
        self,
        youtube_connector: Optional[YouTubeDataConnector] = None,
        multi_connector: Optional[MultiPlatformSocialConnector] = None,
        repo: Optional[MarketIntelligenceRepository] = None
    ):
        self.youtube_connector = youtube_connector or YouTubeDataConnector()
        self.multi_connector = multi_connector or MultiPlatformSocialConnector()
        self.repo = repo or market_intelligence_repo
        self._in_memory_signals: Dict[str, SocialSignal] = {}

    def record_signal(self, signal: SocialSignal) -> SocialSignal:
        """Stores a verified social signal in the service registry and repository."""
        self._in_memory_signals[signal.id] = signal
        if self.repo:
            try:
                self.repo.save_social_signal(signal)
            except Exception as e:
                logger.warning(f"Failed to persist social signal to repository: {e}")
        return signal

    def list_signals(
        self,
        platform: Optional[str] = None,
        product_id: Optional[str] = None,
        limit: int = 50
    ) -> List[SocialSignal]:
        """Queries stored social signals filtered by platform or matched product ID."""
        if self.repo:
            try:
                signals = self.repo.list_social_signals(platform=platform, product_id=product_id, limit=limit)
                if signals:
                    return signals
            except Exception as e:
                logger.warning(f"Error querying repository for social signals: {e}")

        signals = list(self._in_memory_signals.values())
        if platform and platform.lower() != "all":
            signals = [s for s in signals if s.platform.lower() == platform.lower()]
        if product_id:
            signals = [s for s in signals if s.matched_product_id == product_id or s.matched_unified_id == product_id]

        signals.sort(key=lambda s: s.observed_at, reverse=True)
        return signals[:limit]

    def fetch_live_social_signals(
        self,
        query: str,
        limit: int = 25,
        catalog_products: Optional[List[Any]] = None,
        platform: Optional[str] = None
    ) -> Tuple[List[SocialSignal], bool, Optional[str]]:
        """
        Fetches live social observations from connected platforms and runs product matching.
        Supports YouTube, X/Twitter, TikTok, Instagram, and Facebook.
        """
        processed: List[SocialSignal] = []
        is_live = False
        err = None

        target_platform = (platform or "").lower()
        if target_platform in ["youtube", ""]:
            raw_signals, is_live, err = self.youtube_connector.fetch_signals_with_mode(limit=limit, query=query)
            now = datetime.now(timezone.utc)
            for ps in raw_signals:
                views = int(ps.metadata.get("view_count", 0)) if ps.metadata else 0
                likes = int(ps.metadata.get("like_count", 0)) if ps.metadata else 0
                comments = int(ps.metadata.get("comment_count", 0)) if ps.metadata else 0
                shares = int(ps.metadata.get("share_count", 0)) if ps.metadata else 0

                # Deterministic product matching if catalog is supplied
                matched_pid = None
                matched_uid = None
                match_conf = 0.0

                if catalog_products:
                    match_res = ProductMatchingEngine.match_content_detailed(ps.title, catalog_products)
                    if match_res.product and match_res.confidence >= self.MATCH_CONFIDENCE_THRESHOLD:
                        matched_pid = getattr(match_res.product, "id", None) or getattr(match_res.product, "external_product_id", None)
                        matched_uid = getattr(match_res.product, "unified_product_id", None)
                        match_conf = match_res.confidence

                sig = SocialSignal(
                    id=f"soc_sig_{uuid.uuid4().hex[:12]}",
                    platform=ps.platform or "YouTube",
                    external_id=ps.id,
                    content_title=ps.title,
                    content_url=ps.url,
                    author_name=ps.author,
                    views=views,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    engagement_rate=ps.engagement_rate or 0.0,
                    matched_product_id=matched_pid,
                    matched_unified_id=matched_uid,
                    match_confidence=match_conf,
                    observed_at=ps.timestamp or now,
                    raw_metadata=ps.metadata or {},
                    created_at=now
                )
                self.record_signal(sig)
                processed.append(sig)

        # Multi-platform channels (X/Twitter, TikTok, Instagram, Facebook)
        if target_platform in ["twitter", "x", "x/twitter", "tiktok", "instagram", "facebook", "all", "multi"]:
            extra_sigs, meta = self.multi_connector.fetch_all(query=query, limit_per_platform=limit)
            for s in extra_sigs:
                if target_platform not in ["all", "multi"] and s.platform.lower() != target_platform and (target_platform in ["twitter", "x"] and s.platform != "X/Twitter"):
                    continue
                if catalog_products:
                    match_res = ProductMatchingEngine.match_content_detailed(s.content_title, catalog_products)
                    if match_res.product and match_res.confidence >= self.MATCH_CONFIDENCE_THRESHOLD:
                        s.matched_product_id = getattr(match_res.product, "id", None) or getattr(match_res.product, "external_product_id", None)
                        s.matched_unified_id = getattr(match_res.product, "unified_product_id", None)
                        s.match_confidence = match_res.confidence
                self.record_signal(s)
                processed.append(s)
            if not is_live and any(m.get("is_live") for m in meta.get("platform_statuses", {}).values()):
                is_live = True

        return processed, is_live, err

    def get_product_social_metrics(
        self,
        product_id: str,
        product_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregates social demand metrics for a specific product.
        Returns empty/neutral structure if no real social signals exist.
        """
        signals = [s for s in self._in_memory_signals.values() if s.matched_product_id == product_id or s.matched_unified_id == product_id]

        if not signals and product_title:
            # Check for title match among existing market signals
            cleaned = product_title.lower()
            matching_signals = []
            for s in self._in_memory_signals.values():
                if len(cleaned) > 4 and cleaned in s.content_title.lower():
                    s.matched_product_id = product_id
                    matching_signals.append(s)
            signals = matching_signals

        if not signals:
            return {
                "mentions_count": 0,
                "total_views": 0,
                "total_likes": 0,
                "total_comments": 0,
                "total_shares": 0,
                "engagement_rate": 0.0,
                "platforms": [],
                "signals": [],
                "viral_evaluation": {
                    "viral_score": None,
                    "viral_level": "unavailable",
                    "confidence": 0.0,
                    "has_social_signals": False,
                    "supporting_signals": []
                }
            }

        views = sum(s.views for s in signals)
        likes = sum(s.likes for s in signals)
        comments = sum(s.comments for s in signals)
        shares = sum(s.shares for s in signals)
        avg_eng = round(sum(s.engagement_rate for s in signals) / len(signals), 4)
        plats = sorted(list(set(s.platform for s in signals)))

        viral_eval = ViralPotentialEngine.evaluate_from_social_signals(signals)

        return {
            "mentions_count": len(signals),
            "total_views": views,
            "total_likes": likes,
            "total_comments": comments,
            "total_shares": shares,
            "engagement_rate": avg_eng,
            "platforms": plats,
            "signals": signals,
            "viral_evaluation": viral_eval
        }

    def get_social_overview(self, keyword: Optional[str] = None) -> SocialIntelligenceResponse:
        """Returns aggregate overview of social demand signals across platforms."""
        signals = list(self._in_memory_signals.values())
        if keyword:
            kw = keyword.lower()
            signals = [s for s in signals if kw in s.content_title.lower()]

        items: List[SocialSignalItem] = []
        for s in signals[:50]:
            items.append(
                SocialSignalItem(
                    id=s.id,
                    platform=s.platform,
                    content_title=s.content_title,
                    content_url=s.content_url,
                    author_name=s.author_name,
                    views=s.views,
                    likes=s.likes,
                    comments=s.comments,
                    shares=s.shares,
                    engagement_rate=s.engagement_rate,
                    matched_product_id=s.matched_product_id,
                    match_confidence=s.match_confidence,
                    observed_at=s.observed_at
                )
            )

        total_views = sum(s.views for s in signals)
        total_eng = sum(s.likes + s.comments + s.shares for s in signals)
        platforms = sorted(list(set(s.platform for s in signals)))

        return SocialIntelligenceResponse(
            signals=items,
            total_signals=len(items),
            total_views=total_views,
            total_engagement=total_eng,
            platforms=platforms
        )
