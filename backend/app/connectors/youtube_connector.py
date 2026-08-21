import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import logging
from backend.app.domain.signals import PlatformSignal
from backend.app.connectors.base import DataSourceConnector
from backend.app.core.config import settings
from backend.app.core.http_client import (
    ResilientHTTPClient, RateLimitException, QuotaExceededException, AuthenticationException
)

logger = logging.getLogger("trendpulse.connectors.youtube")

_DEFAULT_API_KEY = object()

class YouTubeDataConnector(DataSourceConnector):
    """
    Production-grade connector for YouTube Data API v3.
    Extracts video view counts, like counts, comment metrics, and publication dates
    for trending e-commerce and consumer products.
    """

    DEFAULT_QUERIES = [
        "viral product review 2026",
        "tiktok made me buy it",
        "top trending gadget review",
        "best tech under $100 2026",
        "unboxing viral trending"
    ]

    def __init__(self, api_key: Any = _DEFAULT_API_KEY, http_client: Optional[ResilientHTTPClient] = None):
        if api_key is _DEFAULT_API_KEY:
            self.api_key = settings.YOUTUBE_API_KEY or ""
        else:
            self.api_key = api_key or ""
        self.base_url = settings.YOUTUBE_API_BASE_URL
        self.http_client = http_client or ResilientHTTPClient()

    @property
    def platform_name(self) -> str:
        return "YouTube"

    @property
    def platform_slug(self) -> str:
        return "youtube"

    @property
    def is_live_configured(self) -> bool:
        """Returns True if a real API key is configured."""
        return bool(self.api_key and self.api_key.strip() and self.api_key != "PASTE_YOUR_YOUTUBE_API_KEY_HERE")

    def test_connection(self) -> bool:
        """
        Verifies API connectivity.
        """
        if not self.is_live_configured:
            return True
        try:
            url = f"{self.base_url}/search"
            params = {
                "part": "snippet",
                "q": "trending",
                "maxResults": 1,
                "key": self.api_key
            }
            self.http_client.get(url, params=params)
            return True
        except (AuthenticationException, QuotaExceededException) as e:
            logger.error(f"YouTube connection authentication/quota failure: {e}")
            return False
        except Exception as e:
            logger.error(f"YouTube connection test failed: {e}")
            return False

    def fetch_signals_with_mode(self, limit: int = 50, query: Optional[str] = None) -> Tuple[List[PlatformSignal], bool, Optional[str]]:
        """
        Fetches signals returning: (signals, is_live, error_message)
        """
        if not self.is_live_configured:
            return self._fetch_offline_signals(limit=limit), False, None

        signals: List[PlatformSignal] = []
        queries = [query] if query else self.DEFAULT_QUERIES
        max_per_query = max(limit // len(queries), 5)
        last_error = None

        for q in queries:
            try:
                # 1. Search for videos
                search_url = f"{self.base_url}/search"
                search_params = {
                    "part": "snippet",
                    "q": q,
                    "type": "video",
                    "maxResults": min(max_per_query, settings.YOUTUBE_MAX_RESULTS),
                    "regionCode": settings.YOUTUBE_REGION_CODE,
                    "relevanceLanguage": settings.YOUTUBE_LANGUAGE,
                    "key": self.api_key
                }
                search_res = self.http_client.get(search_url, params=search_params)
                items = search_res.get("items", [])
                video_ids = [item["id"]["videoId"] for item in items if "videoId" in item.get("id", {})]

                if not video_ids:
                    continue

                # 2. Fetch video statistics
                videos_url = f"{self.base_url}/videos"
                videos_params = {
                    "part": "snippet,statistics",
                    "id": ",".join(video_ids),
                    "key": self.api_key
                }
                videos_res = self.http_client.get(videos_url, params=videos_params)
                
                # 3. Normalize videos into PlatformSignal
                for v in videos_res.get("items", []):
                    signal = self._normalize_youtube_video(v)
                    if signal:
                        signals.append(signal)

            except (QuotaExceededException, AuthenticationException, RateLimitException) as e:
                logger.error(f"YouTube live API error: {e}")
                last_error = str(e)
                break
            except Exception as e:
                logger.error(f"Failed to fetch live YouTube signals for '{q}': {e}")
                last_error = str(e)

        if not signals:
            if last_error:
                # In live mode with an error, fall back with warning error captured
                return self._fetch_offline_signals(limit=limit), False, last_error
            return self._fetch_offline_signals(limit=limit), False, None

        return signals[:limit], True, None

    def fetch_signals(self, limit: int = 50, query: Optional[str] = None) -> List[PlatformSignal]:
        signals, _, _ = self.fetch_signals_with_mode(limit=limit, query=query)
        return signals

    def _normalize_youtube_video(self, item: Dict[str, Any]) -> Optional[PlatformSignal]:
        try:
            vid_id = item.get("id", "")
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})

            title = snippet.get("title", "")
            desc = snippet.get("description", "")
            published_str = snippet.get("publishedAt")
            
            if published_str:
                published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            else:
                published_at = datetime.now(timezone.utc)

            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments = int(stats.get("commentCount", 0))

            if views <= 0:
                views = max(likes * 15, 1000)

            eng_rate = (likes + comments) / max(views, 1.0)
            eng_rate = min(max(eng_rate, 0.01), 0.35)

            # Sentiment heuristic based on positive/negative keyword presence
            text = f"{title} {desc}".lower()
            pos_words = ["best", "love", "amazing", "viral", "must have", "great", "review", "haul", "favorite"]
            neg_words = ["worst", "don't buy", "scam", "broken", "terrible", "waste"]
            
            pos_count = sum(1 for w in pos_words if w in text)
            neg_count = sum(1 for w in neg_words if w in text)
            sentiment = 0.8 + (pos_count * 0.04) - (neg_count * 0.15)
            sentiment = round(min(max(sentiment, 0.3), 0.98), 2)

            return PlatformSignal(
                id=f"sig_yt_{vid_id or uuid.uuid4().hex[:6]}",
                platform="YouTube",
                product_id="unmatched",  # Matched later by ProductMatchingEngine
                product_name=title,
                category="General",
                timestamp=published_at,
                volume=views,
                engagement_rate=round(eng_rate, 4),
                shares_count=int(likes * 0.4),
                views_count=views,
                likes_count=likes,
                comments_count=comments,
                sentiment_score=sentiment,
                mode="live",
                source_url=f"https://youtube.com/watch?v={vid_id}" if vid_id else None,
                raw_payload={"video_id": vid_id, "channel": snippet.get("channelTitle"), "description": desc}
            )
        except Exception as e:
            logger.warning(f"Error normalizing YouTube video: {e}")
            return None

    def _fetch_offline_signals(self, limit: int = 50) -> List[PlatformSignal]:
        now = datetime.now(timezone.utc)
        signals = [
            PlatformSignal(
                id=f"sig_yt_{uuid.uuid4().hex[:6]}",
                platform="YouTube",
                product_id="prod_02",
                product_name="TitanFlex Modular Running Vest — Long Run Review & Fluid Capacity Test",
                category="Sports & Outdoor",
                timestamp=now,
                volume=138000,
                engagement_rate=0.082,
                shares_count=18500,
                views_count=138000,
                likes_count=9400,
                comments_count=1820,
                sentiment_score=0.92,
                mode="mock",
                source_url="https://youtube.com/watch?v=titanflex_review_2026",
                raw_payload={"video_id": "titanflex_review_2026", "channel": "EnduranceGearPro"}
            ),
            PlatformSignal(
                id=f"sig_yt_{uuid.uuid4().hex[:6]}",
                platform="YouTube",
                product_id="prod_01",
                product_name="HydroGlow Thermal Lip Serum Color Shift Wear Test (All 6 Shades)",
                category="Beauty & Personal Care",
                timestamp=now,
                volume=192000,
                engagement_rate=0.095,
                shares_count=31000,
                views_count=192000,
                likes_count=16800,
                comments_count=2940,
                sentiment_score=0.95,
                mode="mock",
                source_url="https://youtube.com/watch?v=hydroglow_swatches",
                raw_payload={"video_id": "hydroglow_swatches", "channel": "CosmeticLabReviews"}
            ),
            PlatformSignal(
                id=f"sig_yt_{uuid.uuid4().hex[:6]}",
                platform="YouTube",
                product_id="prod_03",
                product_name="MagSnap 3-in-1 Foldable Stand — Best Travel MagSafe Charger 2026?",
                category="Consumer Electronics",
                timestamp=now,
                volume=84000,
                engagement_rate=0.076,
                shares_count=9200,
                views_count=84000,
                likes_count=5800,
                comments_count=870,
                sentiment_score=0.89,
                mode="mock",
                source_url="https://youtube.com/watch?v=magsnap_edc_review",
                raw_payload={"video_id": "magsnap_edc_review", "channel": "MinimalDeskTech"}
            ),
            PlatformSignal(
                id=f"sig_yt_{uuid.uuid4().hex[:6]}",
                platform="YouTube",
                product_id="prod_04",
                product_name="Traditional Matcha Ceremonial Whisk Set Preparation Routine",
                category="Home & Living",
                timestamp=now,
                volume=65000,
                engagement_rate=0.084,
                shares_count=7800,
                views_count=65000,
                likes_count=5100,
                comments_count=720,
                sentiment_score=0.91,
                mode="mock",
                source_url="https://youtube.com/watch?v=ceremonial_matcha_guide",
                raw_payload={"video_id": "ceremonial_matcha_guide", "channel": "ZenLivingRoutines"}
            )
        ]
        return signals[:limit]
