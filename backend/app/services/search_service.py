from typing import List, Optional, Any
import logging
from backend.app.schemas.entities import SearchResultItem, SearchResponse
from backend.app.repositories.base import (
    ProductRepository, CategoryRepository, PlatformRepository, ReportRepository, AlertRepository,
    MarketplaceProductRepository
)

logger = logging.getLogger(__name__)

class SearchService:
    """
    Executes cross-entity ranked search across products, categories,
    platforms, reports, active anomaly alerts, and real-time Daraz Pakistan catalog.
    """

    def __init__(
        self,
        products: ProductRepository,
        categories: CategoryRepository,
        platforms: PlatformRepository,
        reports: ReportRepository,
        alerts: AlertRepository,
        daraz_service: Optional[Any] = None,
        marketplace_repo: Optional[MarketplaceProductRepository] = None
    ):
        self.products = products
        self.categories = categories
        self.platforms = platforms
        self.reports = reports
        self.alerts = alerts
        self.daraz_service = daraz_service
        self.marketplace_repo = marketplace_repo

    def search(self, query_str: str) -> SearchResponse:
        q = query_str.strip().lower()
        if not q:
            return SearchResponse(query=query_str, total_results=0, results=[])

        results: List[SearchResultItem] = []
        seen_ids = set()

        # 1. Search Local Ingested Products
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
                seen_ids.add(p.id)

        # 1b. Search Persisted Marketplace Products
        if self.marketplace_repo:
            try:
                for mp in self.marketplace_repo.list_products(limit=200):
                    pid = mp.id if mp.id.startswith(f"{mp.platform}_") else f"{mp.platform}_{mp.product_id}"
                    if pid in seen_ids or mp.product_id in seen_ids:
                        continue
                    if q in mp.product_name.lower() or (mp.category and q in mp.category.lower()) or (mp.brand and q in mp.brand.lower()):
                        p_title = (mp.platform or "daraz").title()
                        price_display = f"{mp.currency} {mp.price:,.0f}" if mp.price > 0 else "Price on Request"
                        rating_display = f"★ {mp.rating:.1f}" if mp.rating > 0 else "Verified"
                        results.append(
                            SearchResultItem(
                                id=pid,
                                title=mp.product_name,
                                subtitle=f"{p_title} • {price_display} • {rating_display}",
                                category="products",
                                link=f"/products/{pid}",
                                badge=f"{p_title} PK"
                            )
                        )
                        seen_ids.add(pid)
                        seen_ids.add(mp.id)
            except Exception as e:
                logger.debug(f"Marketplace repo search error: {e}")

        # 2. Search Live Daraz Pakistan Products via Connector
        if self.daraz_service:
            try:
                daraz_res = self.daraz_service.search_products(query=query_str, page=1)
                for dp in daraz_res.products[:8]:  # Top 8 live marketplace matches
                    price_display = f"PKR {dp.price:,.0f}" if dp.price > 0 else "Price on Request"
                    rating_display = f"★ {dp.rating:.1f}" if dp.rating > 0 else "New"
                    seller_display = f" • {dp.seller_name}" if dp.seller_name else ""
                    results.append(
                        SearchResultItem(
                            id=f"daraz_{dp.product_id}",
                            title=dp.name,
                            subtitle=f"Daraz PK • {price_display} • {rating_display}{seller_display}",
                            category="products",
                            link=f"/products/daraz_{dp.product_id}",
                            badge="Daraz Pakistan"
                        )
                    )
            except Exception as e:
                logger.warning(f"Daraz search integration error for '{query_str}': {e}")

        # 3. Search Categories
        for c in self.categories.list():
            c_name = (c.name or "").lower()
            c_desc = (c.description or "").lower()
            if q in c_name or q in c_desc:
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

        # 4. Search Platforms
        for pl in self.platforms.list():
            pl_name = (pl.name or "").lower()
            pl_slug = (pl.slug or "").lower()
            if q in pl_name or q in pl_slug:
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

        # 5. Search Reports
        for r in self.reports.list():
            r_title = (r.title or "").lower()
            r_template = (r.template or "").lower()
            r_takeaways = (r.ai_takeaways or "").lower()
            if q in r_title or q in r_template or q in r_takeaways:
                results.append(
                    SearchResultItem(
                        id=r.id,
                        title=r.title,
                        subtitle=f"Template: {r.template.title() if r.template else ''} • {r.created_at.strftime('%b %d, %Y') if r.created_at else ''}",
                        category="reports",
                        link=f"/reports/{r.id}",
                        badge="Report"
                    )
                )

        # 6. Search Alerts
        for a in self.alerts.list():
            a_title = (a.title or "").lower()
            a_desc = (a.description or "").lower()
            if q in a_title or q in a_desc:
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

