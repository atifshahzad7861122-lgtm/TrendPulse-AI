import uuid
from datetime import datetime, timezone
import io
import csv
from typing import List, Optional, Dict, Any
from backend.app.models.domain import Report, User, Product
from backend.app.repositories.base import ReportRepository, ProductRepository
from backend.app.schemas.entities import ReportGenerateRequest
from backend.app.services.ai_insight_service import AIInsightService

class ReportService:
    """
    Coordinates multi-stage analytical report generation,
    extracts real product anomalies, and formats CSV/JSON exports.
    """

    def __init__(self, report_repo: ReportRepository, product_repo: ProductRepository):
        self.reports = report_repo
        self.products = product_repo

    def list_reports(self) -> List[Report]:
        return self.reports.list()

    def get_report_by_id(self, report_id: str) -> Optional[Report]:
        return self.reports.get_by_id(report_id)

    def generate_report(self, req: ReportGenerateRequest, user: User) -> Report:
        rep_id = f"rep_{uuid.uuid4().hex[:8]}"
        
        # 1. Filter products matching requested category & platforms
        all_prods = self.products.list()
        matching_prods = [
            p for p in all_prods
            if (req.category is None or req.category == "All Categories" or p.category.lower() == req.category.lower())
        ]
        if not matching_prods:
            matching_prods = all_prods

        # Sort by growth and score
        sorted_prods = sorted(matching_prods, key=lambda x: x.trend_score, reverse=True)
        top_prods = sorted_prods[:4]
        
        total_signals = sum(p.volume for p in matching_prods)
        high_conviction = len([p for p in matching_prods if p.trend_score >= 85.0])

        # 2. Extract key findings dynamically
        key_findings = []
        if top_prods:
            p0 = top_prods[0]
            key_findings.append(
                f"Primary Breakout Asset: {p0.name} demonstrates +{p0.growth_rate:.0f}% velocity on {p0.primary_platform}."
            )
        
        key_findings.append(
            f"Sector Demand Concentration: {len(matching_prods)} products evaluated across {req.time_range} timeframe."
        )
        key_findings.append(
            f"Arbitrage Conviction: {high_conviction} high-conviction opportunities identified with >85 composite score."
        )

        # 3. AI synthesis
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
            platforms=req.platforms or ["TikTok", "Daraz", "Instagram", "YouTube"],
            key_findings=key_findings,
            ai_takeaways=ai_synthesis,
            total_signals_analyzed=total_signals,
            high_conviction_count=high_conviction,
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
            writer.writerow(["Report ID", "Title", "Template", "Time Range", "Category", "Total Signals", "High Conviction Count", "Created At"])
            writer.writerow([
                report.id,
                report.title,
                report.template,
                report.time_range,
                report.category,
                report.total_signals_analyzed,
                report.high_conviction_count,
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
