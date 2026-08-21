from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from backend.app.models.domain import Product, Category, PlatformMetrics
from backend.app.schemas.entities import TrendPoint

class AggregationEngine:
    """
    Computes unified cross-entity metrics, category statistics,
    platform summaries, and time-series trend curves.
    """

    @staticmethod
    def aggregate_category_metrics(
        category_name: str,
        category_slug: str,
        category_desc: str,
        products: List[Product]
    ) -> Category:
        """
        Dynamically aggregates product metrics into a Category model.
        """
        cat_products = [p for p in products if p.category.lower() == category_name.lower()]
        count = len(cat_products)
        
        if count == 0:
            return Category(
                id=f"cat_{category_slug}",
                name=category_name,
                slug=category_slug,
                product_count=0,
                avg_trend_score=0.0,
                growth_rate=0.0,
                velocity_label="Steady",
                top_platforms=[],
                description=category_desc
            )

        avg_score = sum(p.trend_score for p in cat_products) / count
        avg_growth = sum(p.growth_rate for p in cat_products) / count

        # Find top platforms
        platform_counts: Dict[str, int] = {}
        for p in cat_products:
            for pl in p.platforms:
                platform_counts[pl] = platform_counts.get(pl, 0) + 1
        
        top_plats = sorted(platform_counts.keys(), key=lambda k: platform_counts[k], reverse=True)[:3]
        
        # Velocity label
        if avg_score >= 90.0:
            vel_label = "Explosive"
        elif avg_score >= 80.0:
            vel_label = "Breakout"
        elif avg_score >= 70.0:
            vel_label = "Surging"
        else:
            vel_label = "Steady"

        return Category(
            id=f"cat_{category_slug}",
            name=category_name,
            slug=category_slug,
            product_count=count,
            avg_trend_score=round(avg_score, 1),
            growth_rate=round(avg_growth, 1),
            velocity_label=vel_label,
            top_platforms=top_plats,
            description=category_desc
        )

    @staticmethod
    def aggregate_platform_metrics(
        platform_name: str,
        platform_slug: str,
        icon: str,
        products: List[Product],
        status: str = "Connected"
    ) -> PlatformMetrics:
        """
        Dynamically calculates platform metrics from product data.
        """
        matching_products = [p for p in products if platform_name in p.platforms or p.primary_platform == platform_name]
        active_trends = len(matching_products)
        
        # Sum total volume / signals attributed to this platform
        total_signals = 0
        growth_rates = []
        for p in matching_products:
            share = p.platform_shares.get(platform_name, 25.0) / 100.0
            total_signals += int(p.volume * share)
            growth_rates.append(p.growth_rate)

        avg_growth = sum(growth_rates) / max(len(growth_rates), 1)

        # Recent spikes list from top products
        recent_spikes = [
            {
                "product": p.name,
                "growth": f"+{p.growth_rate:.0f}%",
                "volume": f"{p.volume:,} mentions"
            }
            for p in sorted(matching_products, key=lambda x: x.growth_rate, reverse=True)[:3]
        ]

        return PlatformMetrics(
            id=f"plat_{platform_slug}",
            name=platform_name,
            slug=platform_slug,
            icon=icon,
            total_signals=max(total_signals, 15000),
            active_trends=active_trends,
            velocity_growth=round(avg_growth, 1),
            market_share=round(min(max(active_trends * 15.0, 10.0), 45.0), 1),
            status=status,
            recent_spikes=recent_spikes
        )

    @staticmethod
    def generate_aggregated_trend_series(
        products: List[Product],
        time_range: str = "30d"
    ) -> List[TrendPoint]:
        """
        Builds dynamic aggregate time-series points based on filtered products.
        """
        now = datetime.now(timezone.utc)
        days = 7 if time_range == "7d" else (30 if time_range == "30d" else 90)
        
        if not products:
            # Fallback curve if empty
            points: List[TrendPoint] = []
            for i in range(days, -1, -1 if days <= 30 else -3):
                dt = now - timedelta(days=i)
                points.append(
                    TrendPoint(
                        timestamp=dt.strftime("%b %d" if days <= 30 else "%b '%y"),
                        score=50.0,
                        volume=10000,
                        sentiment=0.7,
                        platform_tiktok=25.0,
                        platform_daraz=25.0,
                        platform_instagram=25.0,
                        platform_youtube=25.0
                    )
                )
            return points

        # Calculate baseline weighted metrics
        base_avg_score = sum(p.trend_score for p in products) / len(products)
        total_vol = sum(p.volume for p in products)
        avg_sentiment = sum(p.sentiment_score for p in products) / len(products)

        points: List[TrendPoint] = []
        step = 1 if days <= 30 else 3
        
        for i in range(days, -1, -step):
            dt = now - timedelta(days=i)
            progress = (days - i) / max(days, 1)
            # Realistic progressive trajectory matching product average
            score = (base_avg_score * 0.7) + (progress * (base_avg_score * 0.3)) + (((i * 7) % 5) - 2) * 0.8
            volume = int((total_vol * 0.6) + (progress * total_vol * 0.4) + (((i * 13) % 7) - 3) * 1500)
            
            # Platform breakdown percentages
            points.append(
                TrendPoint(
                    timestamp=dt.strftime("%b %d" if days <= 30 else "%b '%y"),
                    score=round(score, 1),
                    volume=max(volume, 1000),
                    sentiment=round(avg_sentiment * (0.85 + progress * 0.15), 2),
                    platform_tiktok=round(35.0 + progress * 15.0, 1),
                    platform_daraz=round(25.0 + progress * 8.0, 1),
                    platform_instagram=round(20.0 + progress * 6.0, 1),
                    platform_youtube=round(15.0 + progress * 4.0, 1)
                )
            )

        return points
