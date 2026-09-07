import uuid
from datetime import datetime, timezone
import io
import csv
from typing import List, Optional, Dict, Any
from backend.app.models.domain import Report, User, Product, MarketplaceProduct, ProductMarketSnapshot
from backend.app.repositories.base import (
    ReportRepository,
    ProductRepository,
    MarketplaceProductRepository,
    PlatformRepository
)
from backend.app.schemas.entities import ReportGenerateRequest
from backend.app.services.ai_insight_service import AIInsightService


def _marketplace_item_to_product(mp: MarketplaceProduct, snapshots: Optional[List[ProductMarketSnapshot]] = None) -> Product:
    snaps = sorted(snapshots or [], key=lambda s: s.observed_at)
    hist_prices = [{"date": s.observed_at.strftime("%b %d"), "price": s.price} for s in snaps if s.price > 0]
    
    growth_rate = 0.0
    if len(hist_prices) >= 2 and hist_prices[0]["price"] > 0:
        growth_rate = round(((hist_prices[-1]["price"] - hist_prices[0]["price"]) / hist_prices[0]["price"]) * 100, 1)

    hist_scores = []
    if snaps:
        for s in snaps:
            if s.rating and s.rating > 0:
                sc = round(min(99.0, max(50.0, s.rating * 16.0 + min(s.review_count or 0, 100) * 0.1)), 1)
                hist_scores.append({"date": s.observed_at.strftime("%b %d"), "score": sc, "volume": s.review_count or 0})

    if mp.rating and mp.rating > 0:
        score = round(min(99.0, max(50.0, mp.rating * 16.0 + min(mp.review_count or 0, 100) * 0.1)), 1)
        sentiment = round(mp.rating / 5.0, 2)
    else:
        score = 0.0
        sentiment = 0.0

    vel_label = "Breakout" if score >= 85 else ("Surging" if score >= 75 else ("Steady" if score > 0 else "Insufficient Data"))
    platform_title = (mp.platform or "daraz").title()
    brand_name = getattr(mp, "brand", None)

    prod_id = mp.id if mp.id.startswith(f"{mp.platform}_") else f"{mp.platform}_{mp.product_id}"

    return Product(
        id=prod_id,
        name=mp.product_name,
        category=mp.category or "Marketplace",
        sub_category=brand_name or f"{platform_title} Verified",
        trend_score=score,
        growth_rate=growth_rate,
        volume=mp.review_count or 0,
        velocity_label=vel_label,
        status="Active" if mp.in_stock else "Watching",
        price_range=f"{mp.currency} {mp.price:,.0f}" if mp.price > 0 else "Price on Request",
        primary_platform=platform_title,
        platforms=[platform_title],
        platform_shares={platform_title: 1.0},
        historical_scores=hist_scores,
        historical_prices=hist_prices,
        ai_summary=f"{platform_title} verified product with {mp.rating or 0}★ rating ({mp.review_count or 0} reviews) from seller '{mp.seller_name or platform_title}'.",
        signals_count=mp.review_count or 0,
        sentiment_score=sentiment,
        image_url=mp.image_url,
        tags=[t for t in [brand_name, mp.location, f"{platform_title} PK", "Verified"] if t],
        is_watchlisted=False,
        provenance="persisted_marketplace_observations",
        observation_count=1 + len(snaps),
        historical_observation_count=len(snaps),
        data_sufficiency="live_data" if mp.price > 0 else "insufficient_data",
        raw_data={
            "marketplace_product": mp.model_dump() if hasattr(mp, "model_dump") else {},
            "source": f"{mp.platform}.pk",
            "product_url": mp.product_url,
            "location": mp.location,
            "brand": brand_name,
            "original_price": mp.original_price,
            "sku": getattr(mp, "sku", None),
            "seller_name": mp.seller_name,
            "seller_id": mp.seller_id
        }
    )


class ReportService:
    """
    Coordinates multi-stage analytical report generation,
    extracts real product anomalies, and formats CSV/JSON exports.
    """

    def __init__(
        self,
        report_repo: ReportRepository,
        product_repo: ProductRepository,
        marketplace_repo: Optional[MarketplaceProductRepository] = None,
        platform_repo: Optional[PlatformRepository] = None
    ):
        self.reports = report_repo
        self.products = product_repo
        self.marketplace_repo = marketplace_repo
        self.platform_repo = platform_repo

    def list_reports(self) -> List[Report]:
        return self.reports.list()

    def get_report_by_id(self, report_id: str) -> Optional[Report]:
        return self.reports.get_by_id(report_id)

    def generate_report(self, req: ReportGenerateRequest, user: User) -> Report:
        rep_id = f"rep_{uuid.uuid4().hex[:8]}"
        
        # 1. Gather all verified persisted products from ProductRepository and MarketplaceProductRepository
        all_prods: List[Product] = []
        seen_ids = set()

        if self.products:
            for p in self.products.list():
                if p.id not in seen_ids:
                    all_prods.append(p)
                    seen_ids.add(p.id)

        if self.marketplace_repo:
            mps = self.marketplace_repo.list_products(limit=1000)
            for mp in mps:
                clean_pid = mp.product_id or mp.id
                raw_id = mp.id if mp.id.startswith(f"{mp.platform}_") else f"{mp.platform}_{clean_pid}"
                if raw_id not in seen_ids and mp.id not in seen_ids:
                    snaps = self.marketplace_repo.get_snapshots(mp.platform, clean_pid, limit=100)
                    prod = _marketplace_item_to_product(mp, snaps)
                    all_prods.append(prod)
                    seen_ids.add(prod.id)

        # 2. Filter products matching requested category & platforms
        matching_prods = []
        for p in all_prods:
            cat_match = True
            if req.category and req.category.strip() and req.category != "All Categories":
                cat_match = p.category.lower() == req.category.lower() or (
                    req.category.lower() in p.category.lower()
                )

            plat_match = True
            if req.platforms and len(req.platforms) > 0:
                req_plats = [pl.lower() for pl in req.platforms]
                plat_match = any(pl.lower() in req_plats for pl in (p.platforms or [p.primary_platform]))

            if cat_match and plat_match:
                matching_prods.append(p)

        # Sort by growth and trend score
        sorted_prods = sorted(matching_prods, key=lambda x: (x.trend_score, x.growth_rate, x.volume), reverse=True)
        top_prods = sorted_prods[:4]
        
        products_evaluated = len(matching_prods)
        total_signals = sum(p.volume for p in matching_prods if p.volume > 0)
        observation_count = sum(getattr(p, "observation_count", 1) for p in matching_prods)
        historical_observation_count = sum(getattr(p, "historical_observation_count", 0) for p in matching_prods)
        
        # High conviction requires score >= 85 backed by verified observation evidence
        high_conviction = len([
            p for p in matching_prods
            if p.trend_score >= 85.0 and p.trend_score > 0 and (getattr(p, "historical_observation_count", 0) > 0 or getattr(p, "growth_rate", 0) != 0)
        ])

        # Platform source breakdown
        source_breakdown: Dict[str, int] = {}
        for p in matching_prods:
            plat = p.primary_platform or "Daraz"
            source_breakdown[plat] = source_breakdown.get(plat, 0) + 1

        active_platforms = list(source_breakdown.keys()) if source_breakdown else (
            [p for p in (req.platforms or ["Daraz"]) if p in ["Daraz", "YouTube"]]
        )

        data_sufficiency = "no_data" if products_evaluated == 0 else (
            "insufficient_data" if historical_observation_count == 0 else "live_data"
        )

        provenance = "persisted_marketplace_observations" if any(
            p.provenance == "persisted_marketplace_observations" for p in matching_prods
        ) else ("live_ingested_signals" if any(
            p.provenance == "live_ingested_signals" for p in matching_prods
        ) else "persisted_observations")

        # 3. Extract key findings dynamically with zero fabricated growth/velocity
        key_findings = []
        if products_evaluated == 0:
            key_findings.append(
                "Sector Demand Concentration: No persisted products or telemetry matching the requested category/platforms."
            )
            key_findings.append(
                "Primary Breakout Asset: Insufficient product observations to establish a lead breakout asset."
            )
            key_findings.append(
                "Arbitrage Conviction: No high conviction opportunities identified from available data."
            )
        else:
            p0 = top_prods[0]
            if p0.trend_score > 0 and p0.growth_rate != 0:
                growth_str = f"+{p0.growth_rate:.1f}%" if p0.growth_rate > 0 else f"{p0.growth_rate:.1f}%"
                key_findings.append(
                    f"Primary Breakout Asset: '{p0.name}' demonstrates {p0.velocity_label} momentum ({growth_str} velocity) on {p0.primary_platform}."
                )
            elif p0.trend_score > 0:
                key_findings.append(
                    f"Primary Breakout Asset: '{p0.name}' recorded with baseline score of {p0.trend_score:.1f} on {p0.primary_platform} (historical velocity: N/A - requires chronological snapshots)."
                )
            else:
                key_findings.append(
                    f"Primary Breakout Asset: '{p0.name}' indexed as baseline observation on {p0.primary_platform} (Score: N/A, Velocity: N/A)."
                )

            key_findings.append(
                f"Sector Demand Concentration: {products_evaluated} product(s) evaluated across {req.time_range} timeframe ({total_signals:,} verified signal observations)."
            )

            if high_conviction > 0:
                key_findings.append(
                    f"Arbitrage Conviction: {high_conviction} high-conviction opportunity target(s) identified with >=85 composite score backed by verified observation evidence."
                )
            else:
                key_findings.append(
                    "Arbitrage Conviction: No high conviction opportunities identified from available data (composite score >=85 with multi-point verification required)."
                )

        # 4. AI synthesis from actual observations
        ai_synthesis = AIInsightService.generate_report_synthesis(
            top_products=top_prods,
            category=req.category or "Global Consumer Catalog",
            template=req.template
        )

        title = req.title or f"{req.template.title()} Intelligence Briefing — {req.category or 'Global'}"

        report = Report(
            id=rep_id,
            title=title,
            template=req.template,
            time_range=req.time_range,
            status="Ready",
            progress=100,
            category=req.category or "All Categories",
            platforms=active_platforms,
            key_findings=key_findings,
            ai_takeaways=ai_synthesis,
            total_signals_analyzed=total_signals,
            high_conviction_count=high_conviction,
            products_evaluated=products_evaluated,
            provenance=provenance,
            data_sufficiency=data_sufficiency,
            observation_count=observation_count,
            historical_observation_count=historical_observation_count,
            source_breakdown=source_breakdown,
            pdf_url=None,
            csv_url=f"/api/v1/reports/{rep_id}/export?format=csv",
            created_by=user.full_name,
            created_at=datetime.now(timezone.utc)
        )

        self.reports.create(report)
        return report

    def export_report_data(self, report_id: str, format_: str = "json") -> Any:
        report = self.get_report_by_id(report_id)
        if not report:
            return None

        if format_.lower() == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Report ID", "Title", "Template", "Time Range", "Category", "Total Signals", "Products Evaluated", "High Conviction Count", "Provenance", "Created At"])
            writer.writerow([
                report.id,
                report.title,
                report.template,
                report.time_range,
                report.category,
                report.total_signals_analyzed,
                report.products_evaluated,
                report.high_conviction_count,
                report.provenance,
                report.created_at.isoformat()
            ])
            writer.writerow([])
            writer.writerow(["Key Findings"])
            for kf in report.key_findings:
                writer.writerow([kf])
            writer.writerow([])
            writer.writerow(["AI Executive Synthesis"])
            writer.writerow([report.ai_takeaways])
            return output.getvalue()

        # Default JSON
        return {
            "report_id": report.id,
            "title": report.title,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "format": "json",
            "data": report.model_dump()
        }
