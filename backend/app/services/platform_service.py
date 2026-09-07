from typing import List, Optional
from backend.app.models.domain import PlatformMetrics
from backend.app.repositories.base import PlatformRepository, ProductRepository, MarketplaceProductRepository
from backend.app.domain.aggregation import AggregationEngine

PLATFORM_DEFINITIONS = [
    ("YouTube", "youtube", "smart_display"),
    ("Daraz", "daraz", "shopping_bag"),
    ("TikTok", "tiktok", "tiktok"),
    ("Instagram", "instagram", "photo_camera"),
    ("Facebook", "facebook", "group"),
]

class PlatformService:
    """
    Computes real-time platform telemetry, activity momentum,
    and channel distribution dynamically from verified signal data.
    """

    def __init__(
        self,
        platform_repo: PlatformRepository,
        product_repo: ProductRepository,
        marketplace_repo: Optional[MarketplaceProductRepository] = None
    ):
        self.platforms = platform_repo
        self.products = product_repo
        self.marketplace_repo = marketplace_repo

    def list_platforms(self) -> List[PlatformMetrics]:
        all_products = self.products.list()
        results: List[PlatformMetrics] = []

        for name, slug, icon in PLATFORM_DEFINITIONS:
            # 1. Daraz: Persisted Marketplace Observations
            if slug == "daraz":
                daraz_mp_products = []
                if self.marketplace_repo:
                    try:
                        daraz_mp_products = self.marketplace_repo.list_products(platform="daraz")
                    except Exception:
                        daraz_mp_products = []
                daraz_prod_signals = [p for p in all_products if "Daraz" in p.platforms or p.primary_platform == "Daraz"]
                total_obs = len(daraz_mp_products) + len(daraz_prod_signals)

                if total_obs > 0:
                    recent_spikes = []
                    if daraz_mp_products:
                        recent_spikes = [
                            {
                                "hashtag": p.product_name[:35],
                                "growth": f"PKR {p.price:.0f}",
                                "signals": f"Rating {p.rating}" if p.rating > 0 else f"{p.review_count} reviews"
                            }
                            for p in daraz_mp_products[:3]
                        ]
                    elif daraz_prod_signals:
                        recent_spikes = [
                            {
                                "hashtag": p.name[:35],
                                "growth": f"+{p.growth_rate:.0f}%",
                                "signals": f"{p.volume:,} mentions"
                            }
                            for p in daraz_prod_signals[:3]
                        ]

                    results.append(
                        PlatformMetrics(
                            id="plat_daraz",
                            name="Daraz",
                            slug="daraz",
                            icon="shopping_bag",
                            total_signals=total_obs,
                            active_trends=total_obs,
                            velocity_growth=round(sum(p.growth_rate for p in daraz_prod_signals) / max(len(daraz_prod_signals), 1), 1) if daraz_prod_signals else 0.0,
                            market_share=round(min(max(total_obs * 5.0, 5.0), 40.0), 1),
                            status="Connected",
                            provenance="persisted_marketplace_observations",
                            observation_count=total_obs,
                            recent_spikes=recent_spikes
                        )
                    )
                else:
                    results.append(
                        PlatformMetrics(
                            id="plat_daraz",
                            name="Daraz",
                            slug="daraz",
                            icon="shopping_bag",
                            total_signals=0,
                            active_trends=0,
                            velocity_growth=0.0,
                            market_share=0.0,
                            status="Insufficient Data",
                            provenance="none",
                            observation_count=0,
                            recent_spikes=[]
                        )
                    )

            # 2. YouTube: Live Ingested Signals
            elif slug == "youtube":
                yt_signals = [p for p in all_products if "YouTube" in p.platforms or p.primary_platform == "YouTube"]
                if yt_signals:
                    metrics = AggregationEngine.aggregate_platform_metrics(
                        platform_name=name,
                        platform_slug=slug,
                        icon=icon,
                        products=all_products,
                        status="Connected"
                    )
                    results.append(metrics)
                else:
                    results.append(
                        PlatformMetrics(
                            id="plat_youtube",
                            name="YouTube",
                            slug="youtube",
                            icon="smart_display",
                            total_signals=0,
                            active_trends=0,
                            velocity_growth=0.0,
                            market_share=0.0,
                            status="Insufficient Data",
                            provenance="none",
                            observation_count=0,
                            recent_spikes=[]
                        )
                    )

            # 3. Unconnected / Coming Soon Channels (TikTok, Instagram, Facebook)
            else:
                results.append(
                    PlatformMetrics(
                        id=f"plat_{slug}",
                        name=name,
                        slug=slug,
                        icon=icon,
                        total_signals=0,
                        active_trends=0,
                        velocity_growth=0.0,
                        market_share=0.0,
                        status="Coming Soon",
                        provenance="none",
                        observation_count=0,
                        recent_spikes=[]
                    )
                )

        return results

    def get_platform_by_slug(self, slug: str) -> Optional[PlatformMetrics]:
        platforms = self.list_platforms()
        for p in platforms:
            if p.slug == slug:
                return p
        return None
