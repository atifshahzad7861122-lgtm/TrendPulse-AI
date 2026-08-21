from typing import List
from backend.app.schemas.entities import SearchResultItem, SearchResponse
from backend.app.repositories.base import (
    ProductRepository, CategoryRepository, PlatformRepository, ReportRepository, AlertRepository
)

class SearchService:
    """
    Executes cross-entity ranked search across products, categories,
    platforms, reports, and active anomaly alerts.
    """

    def __init__(
        self,
        products: ProductRepository,
        categories: CategoryRepository,
        platforms: PlatformRepository,
        reports: ReportRepository,
        alerts: AlertRepository
    ):
        self.products = products
        self.categories = categories
        self.platforms = platforms
        self.reports = reports
        self.alerts = alerts

    def search(self, query_str: str) -> SearchResponse:
        q = query_str.strip().lower()
        if not q:
            return SearchResponse(query=query_str, total_results=0, results=[])

        results: List[SearchResultItem] = []

        # 1. Search Products
        for p in self.products.list():
            score = 0
            if q in p.name.lower():
                score += 50
            if q in p.category.lower():
                score += 30
            if any(q in t.lower() for t in p.tags):
                score += 25
            if q in p.ai_summary.lower():
                score += 10
            
            if score > 0:
                results.append(
                    SearchResultItem(
                        id=p.id,
                        title=p.name,
                        subtitle=f"{p.category} • Score: {p.trend_score:.1f}",
                        category="products",
                        link=f"/products/{p.id}",
                        badge=p.velocity_label
                    )
                )

        # 2. Search Categories
        for c in self.categories.list():
            if q in c.name.lower() or q in c.description.lower():
                results.append(
                    SearchResultItem(
                        id=c.id,
                        title=c.name,
                        subtitle=f"{c.product_count} Products Monitored • Growth: +{c.growth_rate}%",
                        category="categories",
                        link="/categories",
                        badge="Category"
                    )
                )

        # 3. Search Platforms
        for pl in self.platforms.list():
            if q in pl.name.lower() or q in pl.slug.lower():
                results.append(
                    SearchResultItem(
                        id=pl.id,
                        title=pl.name,
                        subtitle=f"{pl.total_signals:,} Ingested Signals • {pl.active_trends} Active Trends",
                        category="platforms",
                        link="/platforms",
                        badge="Platform"
                    )
                )

        # 4. Search Reports
        for r in self.reports.list():
            if q in r.title.lower() or q in r.template.lower() or q in r.ai_takeaways.lower():
                results.append(
                    SearchResultItem(
                        id=r.id,
                        title=r.title,
                        subtitle=f"Template: {r.template.title()} • {r.created_at.strftime('%b %d, %Y')}",
                        category="reports",
                        link=f"/reports/{r.id}",
                        badge="Report"
                    )
                )

        # 5. Search Alerts
        for a in self.alerts.list():
            if q in a.title.lower() or q in a.description.lower():
                results.append(
                    SearchResultItem(
                        id=a.id,
                        title=a.title,
                        subtitle=f"{a.severity} Anomaly • {a.category}",
                        category="alerts",
                        link="/alerts",
                        badge=a.severity
                    )
                )

        return SearchResponse(
            query=query_str,
            total_results=len(results),
            results=results
        )
