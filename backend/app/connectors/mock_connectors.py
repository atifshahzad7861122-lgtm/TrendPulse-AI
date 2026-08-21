import uuid
from datetime import datetime, timedelta, timezone
from typing import List
from backend.app.domain.signals import PlatformSignal
from backend.app.connectors.base import DataSourceConnector

class MockTikTokConnector(DataSourceConnector):
    @property
    def platform_name(self) -> str:
        return "TikTok"

    @property
    def platform_slug(self) -> str:
        return "tiktok"

    def test_connection(self) -> bool:
        return True

    def fetch_signals(self, limit: int = 50) -> List[PlatformSignal]:
        now = datetime.now(timezone.utc)
        signals = [
            PlatformSignal(
                id=f"sig_tk_{uuid.uuid4().hex[:6]}",
                platform="TikTok",
                product_id="prod_01",
                product_name="HydroGlow Thermal Lip Serum",
                category="Beauty & Personal Care",
                timestamp=now - timedelta(minutes=4),
                volume=184200,
                engagement_rate=0.094,
                shares_count=42000,
                views_count=1850000,
                likes_count=320000,
                comments_count=14500,
                sentiment_score=0.94,
                source_url="https://tiktok.com/@beauty_trends/video/101"
            ),
            PlatformSignal(
                id=f"sig_tk_{uuid.uuid4().hex[:6]}",
                platform="TikTok",
                product_id="prod_03",
                product_name="MagSnap 3-in-1 Foldable Stand",
                category="Consumer Electronics",
                timestamp=now - timedelta(minutes=18),
                volume=88000,
                engagement_rate=0.078,
                shares_count=16000,
                views_count=920000,
                likes_count=140000,
                comments_count=6200,
                sentiment_score=0.91,
                source_url="https://tiktok.com/@desksetup/video/202"
            ),
            PlatformSignal(
                id=f"sig_tk_{uuid.uuid4().hex[:6]}",
                platform="TikTok",
                product_id="prod_04",
                product_name="Matcha Ceremonial Whisk Set",
                category="Home & Living",
                timestamp=now - timedelta(minutes=35),
                volume=62000,
                engagement_rate=0.082,
                shares_count=12000,
                views_count=640000,
                likes_count=98000,
                comments_count=4100,
                sentiment_score=0.89,
                source_url="https://tiktok.com/@morning_rituals/video/303"
            )
        ]
        return signals[:limit]

class MockDarazConnector(DataSourceConnector):
    @property
    def platform_name(self) -> str:
        return "Daraz"

    @property
    def platform_slug(self) -> str:
        return "daraz"

    def test_connection(self) -> bool:
        return True

    def fetch_signals(self, limit: int = 50) -> List[PlatformSignal]:
        now = datetime.now(timezone.utc)
        signals = [
            PlatformSignal(
                id=f"sig_dz_{uuid.uuid4().hex[:6]}",
                platform="Daraz",
                product_id="prod_03",
                product_name="MagSnap 3-in-1 Foldable Stand",
                category="Consumer Electronics",
                timestamp=now - timedelta(minutes=28),
                volume=112000,
                engagement_rate=0.065,
                shares_count=4500,
                views_count=340000,
                likes_count=28000,
                comments_count=3200,
                sentiment_score=0.88,
                source_url="https://daraz.pk/products/magsnap-stand"
            ),
            PlatformSignal(
                id=f"sig_dz_{uuid.uuid4().hex[:6]}",
                platform="Daraz",
                product_id="prod_01",
                product_name="HydroGlow Thermal Lip Serum",
                category="Beauty & Personal Care",
                timestamp=now - timedelta(minutes=45),
                volume=34000,
                engagement_rate=0.071,
                shares_count=1800,
                views_count=120000,
                likes_count=14000,
                comments_count=1900,
                sentiment_score=0.86,
                source_url="https://daraz.pk/products/hydroglow-serum"
            )
        ]
        return signals[:limit]

class MockInstagramConnector(DataSourceConnector):
    @property
    def platform_name(self) -> str:
        return "Instagram"

    @property
    def platform_slug(self) -> str:
        return "instagram"

    def test_connection(self) -> bool:
        return True

    def fetch_signals(self, limit: int = 50) -> List[PlatformSignal]:
        now = datetime.now(timezone.utc)
        return [
            PlatformSignal(
                id=f"sig_ig_{uuid.uuid4().hex[:6]}",
                platform="Instagram",
                product_id="prod_04",
                product_name="Matcha Ceremonial Whisk Set",
                category="Home & Living",
                timestamp=now - timedelta(hours=1),
                volume=78000,
                engagement_rate=0.088,
                shares_count=21000,
                views_count=780000,
                likes_count=130000,
                comments_count=4200,
                sentiment_score=0.93,
                source_url="https://instagram.com/reel/matcha101"
            )
        ][:limit]

class MockYouTubeConnector(DataSourceConnector):
    @property
    def platform_name(self) -> str:
        return "YouTube"

    @property
    def platform_slug(self) -> str:
        return "youtube"

    def test_connection(self) -> bool:
        return True

    def fetch_signals(self, limit: int = 50) -> List[PlatformSignal]:
        now = datetime.now(timezone.utc)
        return [
            PlatformSignal(
                id=f"sig_yt_{uuid.uuid4().hex[:6]}",
                platform="YouTube",
                product_id="prod_02",
                product_name="TitanFlex Modular Running Vest",
                category="Sports & Outdoor",
                timestamp=now - timedelta(minutes=12),
                volume=94000,
                engagement_rate=0.075,
                shares_count=14000,
                views_count=520000,
                likes_count=68000,
                comments_count=5400,
                sentiment_score=0.91,
                source_url="https://youtube.com/watch?v=titanflex_review"
            )
        ][:limit]

class MockFacebookConnector(DataSourceConnector):
    @property
    def platform_name(self) -> str:
        return "Facebook"

    @property
    def platform_slug(self) -> str:
        return "facebook"

    def test_connection(self) -> bool:
        return True

    def fetch_signals(self, limit: int = 50) -> List[PlatformSignal]:
        now = datetime.now(timezone.utc)
        return [
            PlatformSignal(
                id=f"sig_fb_{uuid.uuid4().hex[:6]}",
                platform="Facebook",
                product_id="prod_02",
                product_name="TitanFlex Modular Running Vest",
                category="Sports & Outdoor",
                timestamp=now - timedelta(hours=2),
                volume=32000,
                engagement_rate=0.052,
                shares_count=4200,
                views_count=190000,
                likes_count=21000,
                comments_count=1800,
                sentiment_score=0.84,
                source_url="https://facebook.com/groups/running/posts/101"
            )
        ][:limit]
