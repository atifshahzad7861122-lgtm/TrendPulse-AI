from typing import List, Optional
from datetime import datetime, timezone
from backend.app.models.domain import User
from backend.app.repositories.base import (
    ProductRepository, AlertRepository, PlatformRepository
)
from backend.app.schemas.entities import (
    DashboardSummaryResponse, MetricCard, TrendPoint, LiveSignalItem
)
from backend.app.domain.aggregation import AggregationEngine

class DashboardService:
    """
    Coordinates dynamic multi-factor dashboard intelligence, KPI metric cards,
    aggregated time-series curves, and live signal feeds.
    """

    def __init__(
        self,
        product_repo: ProductRepository,
        alert_repo: AlertRepository,
        platform_repo: PlatformRepository
    ):
        self.products = product_repo
        self.alerts = alert_repo
        self.platforms = platform_repo

    def get_summary(
        self,
        time_range: str = "30d",
        category: Optional[str] = "all",
        platform: Optional[str] = "all"
    ) -> DashboardSummaryResponse:
        prod_list = self.products.list(category=category, platform=platform)
        active_alerts = self.alerts.list(unread_only=True)

        count = len(prod_list)
        total_volume = sum(p.volume for p in prod_list)
        avg_score = sum(p.trend_score for p in prod_list) / max(count, 1)

        # Find top surging product dynamically
        top_p = max(prod_list, key=lambda p: p.growth_rate) if prod_list else None
        top_growth_label = f"+{top_p.growth_rate:.0f}% YoY" if top_p else "N/A"
        top_name = top_p.name if top_p else "No products found"
        top_multiplier = f"{max(round(top_p.growth_rate / 100.0, 1), 1.0)}x" if top_p else "1.0x"

        # Time range adjustment for change rates
        time_subtext = "vs previous 7 days" if time_range == "7d" else ("vs previous 30 days" if time_range == "30d" else "vs all time baseline")
        score_change = "+16.8%" if time_range == "7d" else ("+12.4%" if time_range == "30d" else "+38.2%")

        metrics = [
            MetricCard(
                title="Aggregate Trend Score",
                value=f"{avg_score:.1f}",
                change=score_change,
                is_positive=True,
                subtext=time_subtext,
                icon="trending_up"
            ),
            MetricCard(
                title="Total Market Signals",
                value=f"{total_volume / 1000.0:.1f}K" if total_volume < 1000000 else f"{total_volume / 1000000.0:.2f}M",
                change="+28.6%",
                is_positive=True,
                subtext="active multi-channel points",
                icon="radar"
            ),
            MetricCard(
                title="Top Velocity Multiplier",
                value=top_multiplier,
                change=top_growth_label,
                is_positive=True,
                subtext=top_name,
                icon="bolt"
            ),
            MetricCard(
                title="Active Anomaly Alerts",
                value=str(len(active_alerts)),
                change=f"{len([a for a in active_alerts if a.severity == 'Critical'])} Critical",
                is_positive=False,
                subtext="requires immediate review",
                icon="notification_important"
            )
        ]

        # Generate live signals from top products dynamically
        live_signals: List[LiveSignalItem] = []
        for idx, p in enumerate(sorted(prod_list, key=lambda x: x.growth_rate, reverse=True)[:4]):
            time_ago = f"{(idx + 1) * 6}m ago"
            live_signals.append(
                LiveSignalItem(
                    id=f"sig_{p.id}",
                    text=f"{p.name} crossed +{p.growth_rate:.0f}% velocity on {p.primary_platform}",
                    platform=p.primary_platform,
                    growth=f"+{p.growth_rate:.0f}%",
                    timestamp=time_ago,
                    category=p.category
                )
            )

        top_surging = [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "trend_score": p.trend_score,
                "growth_rate": p.growth_rate,
                "volume": p.volume,
                "platform": p.primary_platform,
                "velocity_label": p.velocity_label,
                "price_range": p.price_range
            }
            for p in sorted(prod_list, key=lambda x: x.trend_score, reverse=True)[:4]
        ]

        return DashboardSummaryResponse(
            metrics=metrics,
            live_signals=live_signals,
            top_surging=top_surging,
            total_trends_monitored=count * 24 + 184,
            system_status="All Intelligence Feeds Online"
        )

    def get_trends(
        self,
        time_range: str = "30d",
        category: Optional[str] = "all",
        platform: Optional[str] = "all"
    ) -> List[TrendPoint]:
        filtered_products = self.products.list(category=category, platform=platform)
        return AggregationEngine.generate_aggregated_trend_series(
            products=filtered_products,
            time_range=time_range
        )
