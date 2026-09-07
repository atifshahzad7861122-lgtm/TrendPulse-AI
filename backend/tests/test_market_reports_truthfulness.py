import pytest
from datetime import datetime, timezone, timedelta
from backend.app.models.domain import Product, MarketplaceProduct, ProductMarketSnapshot, User
from backend.app.repositories.in_memory import (
    InMemoryReportRepository,
    InMemoryProductRepository,
    InMemoryMarketplaceProductRepository,
    InMemoryPlatformRepository
)
from backend.app.schemas.entities import ReportGenerateRequest
from backend.app.services.report_service import ReportService


def test_empty_database_produces_no_synthetic_report_metrics():
    """Verify generating a report on an empty database yields 0 signals, 0 products evaluated, and no fake convictions."""
    rep_repo = InMemoryReportRepository()
    prod_repo = InMemoryProductRepository()
    mp_repo = InMemoryMarketplaceProductRepository()
    platform_repo = InMemoryPlatformRepository()

    prod_repo._products.clear()
    mp_repo._products.clear()
    rep_repo._reports.clear()

    service = ReportService(
        report_repo=rep_repo,
        product_repo=prod_repo,
        marketplace_repo=mp_repo,
        platform_repo=platform_repo
    )
    user = User(id="usr_qa_1", email="qa@trendpulse.ai", full_name="QA Auditor", hashed_password="hash")

    req = ReportGenerateRequest(
        title="Empty Store Audit Briefing",
        template="executive",
        time_range="30d",
        category="All Categories",
        platforms=["Daraz", "TikTok", "YouTube"]
    )

    report = service.generate_report(req, user)

    assert report.total_signals_analyzed == 0
    assert report.products_evaluated == 0
    assert report.high_conviction_count == 0
    assert report.data_sufficiency == "no_data"
    assert report.total_signals_analyzed != 925100
    assert report.total_signals_analyzed != 482000
    assert "No persisted products or telemetry" in report.key_findings[0]
    assert "No market report intelligence available" in report.ai_takeaways


def test_report_generation_from_real_persisted_daraz_products():
    """Verify generating a report using real persisted Daraz products calculates truthful observations and provenance."""
    rep_repo = InMemoryReportRepository()
    prod_repo = InMemoryProductRepository()
    mp_repo = InMemoryMarketplaceProductRepository()
    platform_repo = InMemoryPlatformRepository()

    prod_repo._products.clear()
    mp_repo._products.clear()
    rep_repo._reports.clear()

    now = datetime.now(timezone.utc)
    
    # 1. Product with 1 observation
    mp1 = MarketplaceProduct(
        id="daraz_item_11",
        product_id="11",
        platform="daraz",
        product_name="Lenovo Thinkplus T50 Wireless Earbuds",
        price=1850.0,
        currency="PKR",
        rating=4.6,
        review_count=35,
        in_stock=True
    )
    mp_repo.upsert_product(mp1)

    # 2. Product with 2 chronological snapshots
    mp2 = MarketplaceProduct(
        id="daraz_item_22",
        product_id="22",
        platform="daraz",
        product_name="M90 Pro Bluetooth Gaming Earbuds",
        price=2100.0,
        currency="PKR",
        rating=4.9,
        review_count=120,
        in_stock=True
    )
    mp_repo.upsert_product(mp2)

    snap1 = ProductMarketSnapshot(
        id="snap_22_1",
        platform="daraz",
        product_id="22",
        price=1900.0,
        currency="PKR",
        rating=4.9,
        review_count=100,
        observed_at=now - timedelta(days=7)
    )
    snap2 = ProductMarketSnapshot(
        id="snap_22_2",
        platform="daraz",
        product_id="22",
        price=2100.0,
        currency="PKR",
        rating=4.9,
        review_count=120,
        observed_at=now
    )
    mp_repo.batch_create_snapshots([snap1, snap2])

    service = ReportService(
        report_repo=rep_repo,
        product_repo=prod_repo,
        marketplace_repo=mp_repo,
        platform_repo=platform_repo
    )
    user = User(id="usr_qa_2", email="qa@trendpulse.ai", full_name="QA Auditor", hashed_password="hash")

    req = ReportGenerateRequest(
        title="Daraz Audio Market Dossier",
        template="velocity_surge",
        time_range="30d",
        category="All Categories",
        platforms=["Daraz"]
    )

    report = service.generate_report(req, user)

    # Products evaluated must be exactly 2
    assert report.products_evaluated == 2
    # Total signals is sum of review volumes (35 + 120 = 155)
    assert report.total_signals_analyzed == 155
    assert report.provenance == "persisted_marketplace_observations"
    assert report.data_sufficiency == "live_data"
    assert report.observation_count == 4  # 2 products + 2 snapshots
    assert report.historical_observation_count == 2
    assert "Daraz" in report.source_breakdown
    assert report.source_breakdown["Daraz"] == 2


def test_no_synthetic_constants_in_generated_report():
    """Verify known demo constants (925100, 482000, 340.5%, HydroGlow) never appear in generated reports unless seeded."""
    rep_repo = InMemoryReportRepository()
    prod_repo = InMemoryProductRepository()
    mp_repo = InMemoryMarketplaceProductRepository()
    platform_repo = InMemoryPlatformRepository()

    prod_repo._products.clear()
    mp_repo._products.clear()

    # Add 1 real product
    mp = MarketplaceProduct(
        id="daraz_item_99",
        product_id="99",
        platform="daraz",
        product_name="Silicone Non-Slip Sports Grip",
        price=450.0,
        currency="PKR",
        rating=4.0,
        review_count=10,
        in_stock=True
    )
    mp_repo.upsert_product(mp)

    service = ReportService(
        report_repo=rep_repo,
        product_repo=prod_repo,
        marketplace_repo=mp_repo,
        platform_repo=platform_repo
    )
    user = User(id="usr_qa_3", email="qa@trendpulse.ai", full_name="QA Auditor", hashed_password="hash")

    req = ReportGenerateRequest(
        title="Accessories Pulse Report",
        template="executive",
        time_range="7d",
        category="All Categories"
    )

    report = service.generate_report(req, user)

    assert report.total_signals_analyzed != 925100
    assert report.total_signals_analyzed != 482000
    assert report.total_signals_analyzed == 10
    assert report.products_evaluated == 1
    # Because only 1 snapshot exists, growth is N/A / 0.0 and velocity is N/A
    assert "340%" not in str(report.key_findings)
    assert "HydroGlow" not in str(report.key_findings)
    assert "TitanFlex" not in str(report.key_findings)


def test_export_report_data_includes_provenance():
    """Verify CSV and JSON export formats contain products_evaluated and provenance."""
    rep_repo = InMemoryReportRepository()
    prod_repo = InMemoryProductRepository()
    prod_repo._products.clear()
    rep_repo._reports.clear()

    service = ReportService(report_repo=rep_repo, product_repo=prod_repo)
    user = User(id="usr_qa_4", email="qa@trendpulse.ai", full_name="QA Auditor", hashed_password="hash")

    req = ReportGenerateRequest(title="Provenance Export Test", template="executive", time_range="30d")
    report = service.generate_report(req, user)

    csv_data = service.export_report_data(report.id, format_="csv")
    assert "Products Evaluated" in csv_data
    assert "Provenance" in csv_data

    json_data = service.export_report_data(report.id, format_="json")
    assert json_data["data"]["products_evaluated"] == 0
    assert json_data["data"]["provenance"] == "persisted_observations"


def test_category_and_platform_filtering_truthful():
    """Verify report generation respects category and platform filters truthfully."""
    rep_repo = InMemoryReportRepository()
    prod_repo = InMemoryProductRepository()
    mp_repo = InMemoryMarketplaceProductRepository()
    platform_repo = InMemoryPlatformRepository()

    prod_repo._products.clear()
    mp_repo._products.clear()

    # Product in Beauty & Personal Care
    mp1 = MarketplaceProduct(
        id="daraz_item_beauty_1",
        product_id="beauty_1",
        platform="daraz",
        product_name="Organic Vitamin C Facial Cleanser",
        category="Beauty & Personal Care",
        price=1200.0,
        currency="PKR",
        rating=4.7,
        review_count=40,
        in_stock=True
    )
    mp_repo.upsert_product(mp1)

    # Product in Electronics
    mp2 = MarketplaceProduct(
        id="daraz_item_elec_1",
        product_id="elec_1",
        platform="daraz",
        product_name="Fast Charging USB-C Hub 6-in-1",
        category="Consumer Electronics",
        price=3400.0,
        currency="PKR",
        rating=4.5,
        review_count=85,
        in_stock=True
    )
    mp_repo.upsert_product(mp2)

    service = ReportService(
        report_repo=rep_repo,
        product_repo=prod_repo,
        marketplace_repo=mp_repo,
        platform_repo=platform_repo
    )
    user = User(id="usr_qa_5", email="qa@trendpulse.ai", full_name="QA Auditor", hashed_password="hash")

    # Generate for Beauty category only
    req = ReportGenerateRequest(
        title="Beauty Specific Briefing",
        template="executive",
        time_range="30d",
        category="Beauty & Personal Care",
        platforms=["Daraz"]
    )
    rep = service.generate_report(req, user)

    assert rep.products_evaluated == 1
    assert rep.total_signals_analyzed == 40
    assert "Organic Vitamin C Facial Cleanser" in rep.key_findings[0]
    assert "Fast Charging" not in str(rep.key_findings)

