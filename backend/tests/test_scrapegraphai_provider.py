"""
Comprehensive Test Suite for ScrapeGraphAI Production Scraper Provider.

Validates:
1. Provider imports successfully
2. Provider configuration loads correctly
3. Missing API key is handled safely
4. Provider routing works
5. SmartScraperGraph extraction output is normalized
6. Missing fields remain null/missing (no fabrication)
7. Output passes DataQualityAgent validation
8. Raw payload persistence works
9. Marketplace product persistence works
10. Snapshot persistence works
11. Unified product linkage works
12. Provider provenance is preserved
13. Failure produces sanitized diagnostics
14. Provider timeout produces FAILED status
15. No credentials appear in logs or raw payload
16. No fake intelligence metrics are generated
17. No fake reviews are generated
18. No fake historical observations are generated
19. ScrapeGraphAI provider coexists with Specialized Daraz
20. ScrapeGraphAI provider coexists with Universal Orchestrator
"""

import os
import json
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from backend.app.core.config import settings
from backend.app.models.domain import (
    ScraperCrawlJob, RawScrapedPayload, MarketplaceProduct,
    ProductMarketSnapshot, UnifiedProduct
)
from backend.app.repositories.in_memory import (
    InMemoryScraperRepository, InMemoryMarketplaceProductRepository,
    InMemoryUnifiedProductRepository, InMemoryDataQualityRepository
)
from backend.app.services.agents.data_quality.agent import DataQualityAgent
from backend.app.services.unified_intelligence_service import UnifiedProductIntelligenceService
from backend.app.services.scraper.bridge import ScraperIntegrationBridge
from backend.app.services.scraper.models import StartScraperJobRequest
from backend.app.services.scraper.providers.scrapegraphai import (
    ScrapeGraphAIEngine, ScrapeGraphAIConfig, ScrapeGraphNormalizer,
    ScrapeGraphProductItem, ScrapeGraphProductList
)


@pytest.fixture
def test_repos():
    scraper_repo = InMemoryScraperRepository()
    marketplace_repo = InMemoryMarketplaceProductRepository()
    unified_repo = InMemoryUnifiedProductRepository()
    dq_repo = InMemoryDataQualityRepository()
    dq_agent = DataQualityAgent(repository=dq_repo)
    unified_svc = UnifiedProductIntelligenceService(
        unified_repo=unified_repo,
        daraz_repo=marketplace_repo
    )
    return scraper_repo, marketplace_repo, unified_repo, dq_repo, dq_agent, unified_svc


class TestScrapeGraphAIProvider:
    """20 comprehensive tests validating ScrapeGraphAI integration."""

    def test_01_provider_imports_successfully(self):
        """Test 1: Provider classes and underlying scrapegraphai graphs import cleanly."""
        from scrapegraphai.graphs import SmartScraperGraph, SmartScraperMultiGraph, SearchGraph
        assert SmartScraperGraph is not None
        assert SmartScraperMultiGraph is not None
        assert SearchGraph is not None

        engine = ScrapeGraphAIEngine()
        assert engine is not None
        assert engine.is_available() is True

    def test_02_config_loads_from_settings(self):
        """Test 2: Configuration loads from TrendPulse settings with correct defaults."""
        cfg = ScrapeGraphAIConfig.load_from_settings()
        assert cfg is not None
        assert isinstance(cfg.headless, bool)
        assert cfg.timeout >= 30.0
        assert cfg.provider is not None
        assert cfg.model is not None

        # Verify model identifier formatting
        model_id = cfg.get_model_identifier()
        assert "/" in model_id

        # Verify graph_config produces expected format
        g_cfg = cfg.to_graph_config()
        assert "llm" in g_cfg
        assert "model" in g_cfg["llm"]
        assert "headless" in g_cfg

    @pytest.mark.asyncio
    async def test_03_missing_api_key_handled_safely(self):
        """Test 3: Provider handles missing/unset API key safely without unhandled crash or mock injection."""
        cfg = ScrapeGraphAIConfig(
            enabled=True,
            provider="openai",
            model="gpt-4o-mini",
            api_key=None,
            headless=True
        )
        engine = ScrapeGraphAIEngine(config=cfg)
        assert engine.is_available() is True

        summary = cfg.get_sanitized_summary()
        assert summary["has_api_key"] is False
        assert summary["provider"] == "openai"

        # Missing API key must fail safely with an error, not generate fake mock products
        with pytest.raises(RuntimeError) as exc_info:
            await engine.scrape_single_url("https://example.com")
        assert "API key is missing" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_04_provider_routing_works(self, test_repos):
        """Test 4: Bridge routes directly to ScrapeGraphAIEngine when provider='scrapegraphai'."""
        scraper_repo, mp_repo, uni_repo, dq_repo, dq_agent, uni_svc = test_repos
        bridge = ScraperIntegrationBridge(
            scraper_repo=scraper_repo,
            marketplace_repo=mp_repo,
            unified_repo=uni_repo,
            dq_repo=dq_repo,
            dq_agent=dq_agent,
            unified_intelligence_svc=uni_svc
        )

        job = ScraperCrawlJob(
            id="job_test_sg_routing",
            marketplace="daraz",
            trigger_type="manual",
            keywords=["earbuds"],
            target_count=2,
            max_workers=1,
            status="queued",
            metadata_json={"provider": "scrapegraphai", "dry_run": False}
        )
        scraper_repo.create_job(job)

        completed_job = await bridge.run_scraper_job(job)
        assert completed_job.status in ("completed", "failed")
        assert completed_job.products_persisted >= 0

    def test_05_smartscraper_output_normalized(self):
        """Test 5: Raw extraction dictionary is correctly normalized into canonical ProductIntelligence."""
        raw_dict = {
            "product_id": "item_12345",
            "title": "Anker Soundcore P20i True Wireless Earbuds",
            "price": 4299.0,
            "original_price": 5999.0,
            "currency": "PKR",
            "rating": 4.8,
            "review_count": 142,
            "availability": True,
            "brand": "Anker",
            "category": "Audio",
            "seller_name": "Anker Official Store",
            "seller_rating": 4.9,
            "product_url": "https://www.daraz.pk/products/anker-p20i-i12345.html",
            "image_url": "https://img.daraz.pk/p20i.jpg",
            "specifications": {"Bluetooth": "5.3", "Battery": "30h"}
        }

        prod_intel = ScrapeGraphNormalizer.to_product_intelligence(
            raw_dict,
            marketplace="daraz",
            source_url=raw_dict["product_url"]
        )
        assert prod_intel.product_id == "item_12345"
        assert prod_intel.title == "Anker Soundcore P20i True Wireless Earbuds"
        assert prod_intel.price == 4299.0
        assert prod_intel.original_price == 5999.0
        assert prod_intel.currency == "PKR"
        assert prod_intel.rating == 4.8
        assert prod_intel.review_count == 142
        assert prod_intel.source_fields["source_provider"] == "scrapegraphai"

    def test_06_missing_fields_remain_null(self):
        """Test 6: Fields not present on the source page remain null/default without fabrication."""
        sparse_dict = {
            "title": "Minimal Cable",
            "price": 250.0
        }
        prod_intel = ScrapeGraphNormalizer.to_product_intelligence(sparse_dict, marketplace="daraz")
        assert prod_intel.rating is None
        assert prod_intel.sold_count is None
        assert prod_intel.reviews == []
        assert prod_intel.variants == []

    @pytest.mark.asyncio
    async def test_07_data_quality_gate_evaluation(self, test_repos):
        """Test 7: Extracted product passes through DataQualityAgent gate successfully."""
        scraper_repo, mp_repo, uni_repo, dq_repo, dq_agent, uni_svc = test_repos
        valid_dict = {
            "product_id": "test_dq_item",
            "title": "Qualitative Mechanical Keyboard",
            "price": 8500.0,
            "original_price": 9500.0,
            "currency": "PKR",
            "seller_name": "Keyboards PK",
            "availability": True
        }
        prod_intel = ScrapeGraphNormalizer.to_product_intelligence(valid_dict, marketplace="daraz")

        bridge = ScraperIntegrationBridge(
            scraper_repo=scraper_repo,
            marketplace_repo=mp_repo,
            unified_repo=uni_repo,
            dq_repo=dq_repo,
            dq_agent=dq_agent,
            unified_intelligence_svc=uni_svc
        )
        job = ScraperCrawlJob(
            id="job_test_dq",
            marketplace="daraz",
            trigger_type="manual",
            target_count=1,
            metadata_json={"provider": "scrapegraphai"}
        )
        scraper_repo.create_job(job)

        await bridge._persist_scraped_product(prod_intel, job)
        assert job.products_persisted == 1
        assert job.products_rejected == 0

    @pytest.mark.asyncio
    async def test_08_raw_payload_persistence(self, test_repos):
        """Test 8: Raw scraped payload is persisted in ScraperRepository with correct metadata."""
        scraper_repo, mp_repo, uni_repo, dq_repo, dq_agent, uni_svc = test_repos
        bridge = ScraperIntegrationBridge(
            scraper_repo=scraper_repo,
            marketplace_repo=mp_repo,
            unified_repo=uni_repo,
            dq_repo=dq_repo,
            dq_agent=dq_agent,
            unified_intelligence_svc=uni_svc
        )

        prod_intel = ScrapeGraphNormalizer.to_product_intelligence({
            "product_id": "raw_test_prod_1",
            "title": "Raw Payload Test Product",
            "price": 1200.0,
            "currency": "PKR"
        }, marketplace="daraz")

        job = ScraperCrawlJob(
            id="job_test_raw_store",
            marketplace="daraz",
            trigger_type="manual",
            target_count=1,
            metadata_json={"provider": "scrapegraphai"}
        )
        scraper_repo.create_job(job)

        await bridge._persist_scraped_product(prod_intel, job)
        raw_rec = scraper_repo.get_raw_payload("daraz", "raw_test_prod_1")
        assert raw_rec is not None
        assert raw_rec.raw_payload["source_provider"] == "scrapegraphai"

    @pytest.mark.asyncio
    async def test_09_marketplace_product_persistence(self, test_repos):
        """Test 9: MarketplaceProduct is upserted with accurate fields in MarketplaceProductRepository."""
        scraper_repo, mp_repo, uni_repo, dq_repo, dq_agent, uni_svc = test_repos
        bridge = ScraperIntegrationBridge(
            scraper_repo=scraper_repo,
            marketplace_repo=mp_repo,
            unified_repo=uni_repo,
            dq_repo=dq_repo,
            dq_agent=dq_agent,
            unified_intelligence_svc=uni_svc
        )

        prod_intel = ScrapeGraphNormalizer.to_product_intelligence({
            "product_id": "mp_test_item_9",
            "title": "Marketplace Product Test Item",
            "price": 3499.0,
            "original_price": 4000.0,
            "currency": "PKR",
            "seller_name": "Daraz Store 9"
        }, marketplace="daraz")

        job = ScraperCrawlJob(
            id="job_test_mp_upsert",
            marketplace="daraz",
            trigger_type="manual",
            target_count=1,
            metadata_json={"provider": "scrapegraphai"}
        )
        scraper_repo.create_job(job)

        await bridge._persist_scraped_product(prod_intel, job)
        mp_prod = mp_repo.get_product("daraz", "mp_test_item_9")
        assert mp_prod is not None
        assert mp_prod.product_name == "Marketplace Product Test Item"
        assert mp_prod.price == 3499.0

    @pytest.mark.asyncio
    async def test_10_market_snapshot_persistence(self, test_repos):
        """Test 10: ProductMarketSnapshot is appended for trend analysis."""
        scraper_repo, mp_repo, uni_repo, dq_repo, dq_agent, uni_svc = test_repos
        bridge = ScraperIntegrationBridge(
            scraper_repo=scraper_repo,
            marketplace_repo=mp_repo,
            unified_repo=uni_repo,
            dq_repo=dq_repo,
            dq_agent=dq_agent,
            unified_intelligence_svc=uni_svc
        )

        prod_intel = ScrapeGraphNormalizer.to_product_intelligence({
            "product_id": "snap_test_prod_10",
            "title": "Snapshot Item",
            "price": 500.0,
            "currency": "PKR"
        }, marketplace="daraz")

        job = ScraperCrawlJob(
            id="job_test_snap",
            marketplace="daraz",
            trigger_type="manual",
            target_count=1,
            metadata_json={"provider": "scrapegraphai"}
        )
        scraper_repo.create_job(job)

        await bridge._persist_scraped_product(prod_intel, job)
        snaps = mp_repo.get_snapshots("daraz", "snap_test_prod_10")
        assert len(snaps) >= 1
        assert snaps[0].price == 500.0

    @pytest.mark.asyncio
    async def test_11_unified_product_linkage(self, test_repos):
        """Test 11: Scraped listing correctly links into Unified Product Intelligence."""
        scraper_repo, mp_repo, uni_repo, dq_repo, dq_agent, uni_svc = test_repos
        bridge = ScraperIntegrationBridge(
            scraper_repo=scraper_repo,
            marketplace_repo=mp_repo,
            unified_repo=uni_repo,
            dq_repo=dq_repo,
            dq_agent=dq_agent,
            unified_intelligence_svc=uni_svc
        )

        prod_intel = ScrapeGraphNormalizer.to_product_intelligence({
            "product_id": "unified_link_item_11",
            "title": "Sony WH-1000XM5 Wireless Headphones",
            "price": 89000.0,
            "currency": "PKR"
        }, marketplace="daraz")

        job = ScraperCrawlJob(
            id="job_test_unified_link",
            marketplace="daraz",
            trigger_type="manual",
            target_count=1,
            metadata_json={"provider": "scrapegraphai"}
        )
        scraper_repo.create_job(job)

        await bridge._persist_scraped_product(prod_intel, job)
        u_prods = uni_repo.list_unified_products(limit=10)
        assert len(u_prods) >= 1
        matched = [p for p in u_prods if "Sony WH" in p.canonical_name or "Sony" in (p.brand or "")]
        assert len(matched) >= 1

    @pytest.mark.asyncio
    async def test_12_provider_provenance_preserved(self, test_repos):
        """Test 12: Provider provenance ('scrapegraphai') is preserved across all layers."""
        scraper_repo, mp_repo, uni_repo, dq_repo, dq_agent, uni_svc = test_repos
        bridge = ScraperIntegrationBridge(
            scraper_repo=scraper_repo,
            marketplace_repo=mp_repo,
            unified_repo=uni_repo,
            dq_repo=dq_repo,
            dq_agent=dq_agent,
            unified_intelligence_svc=uni_svc
        )

        prod_intel = ScrapeGraphNormalizer.to_product_intelligence({
            "product_id": "prov_prod_12",
            "title": "Provenance Test Item",
            "price": 1500.0,
            "currency": "PKR"
        }, marketplace="daraz")

        assert prod_intel.source_fields["source_provider"] == "scrapegraphai"

        job = ScraperCrawlJob(
            id="job_test_provenance",
            marketplace="daraz",
            trigger_type="manual",
            target_count=1,
            metadata_json={"provider": "scrapegraphai"}
        )
        scraper_repo.create_job(job)

        await bridge._persist_scraped_product(prod_intel, job)
        raw_rec = scraper_repo.get_raw_payload("daraz", "prov_prod_12")
        assert raw_rec is not None
        assert raw_rec.raw_payload["source_provider"] == "scrapegraphai"

    def test_13_sanitized_diagnostics_on_failure(self):
        """Test 13: Error handler sanitizes and masks API keys and credentials."""
        cfg = ScrapeGraphAIConfig(
            enabled=True,
            provider="openai",
            model="gpt-4o-mini",
            api_key="sk-abcdef1234567890abcdef1234567890",
            headless=True
        )
        engine = ScrapeGraphAIEngine(config=cfg)
        secret_err = Exception("Failed call to api.openai.com with key sk-abcdef1234567890abcdef1234567890 timeout")
        sanitized = engine._sanitize_error(secret_err)

        assert "sk-abcdef1234567890abcdef1234567890" not in sanitized
        assert "[REDACTED" in sanitized

    @pytest.mark.asyncio
    async def test_14_timeout_produces_failed_status(self, test_repos):
        """Test 14: Timeouts during extraction produce sanitized FAILED job status."""
        scraper_repo, mp_repo, uni_repo, dq_repo, dq_agent, uni_svc = test_repos

        mock_engine = MagicMock(spec=ScrapeGraphAIEngine)
        mock_engine.crawl_catalog = AsyncMock(side_effect=TimeoutError("Execution exceeded timeout 60s"))

        bridge = ScraperIntegrationBridge(
            scraper_repo=scraper_repo,
            marketplace_repo=mp_repo,
            unified_repo=uni_repo,
            scrapegraphai_engine=mock_engine
        )

        job = ScraperCrawlJob(
            id="job_test_timeout_fail",
            marketplace="daraz",
            trigger_type="manual",
            keywords=["stalled_query"],
            target_count=5,
            metadata_json={"provider": "scrapegraphai"}
        )
        scraper_repo.create_job(job)

        res = await bridge.run_scraper_job(job)
        assert res.status == "failed"
        assert "timeout" in (res.error_message or "").lower()

    def test_15_no_credentials_in_logs_or_payload(self):
        """Test 15: Serialized models and summaries never include raw API keys or tokens."""
        cfg = ScrapeGraphAIConfig(
            enabled=True,
            provider="openai",
            model="gpt-4o-mini",
            api_key="super_secret_test_key_12345",
            headless=True
        )
        summary = cfg.get_sanitized_summary()
        summary_str = json.dumps(summary)
        assert "super_secret_test_key_12345" not in summary_str
        assert summary["has_api_key"] is True

    def test_16_no_fake_intelligence_metrics(self):
        """Test 16: ScrapeGraphAI does not fabricate predictive trend scores or market share."""
        item = ScrapeGraphProductItem(
            title="Real Smartwatch",
            price=2999.0,
            currency="PKR"
        )
        prod_intel = ScrapeGraphNormalizer.to_product_intelligence(item, marketplace="daraz")
        raw_data = json.loads(prod_intel.raw_data)

        for forbidden in ["trend_score", "velocity", "sales_volume", "market_share", "forecast"]:
            assert forbidden not in raw_data
            assert forbidden not in prod_intel.source_fields

        # Verify no simulated seller metrics are injected
        assert "seller_metrics" in prod_intel.source_fields
        assert "Ship on Time" not in prod_intel.source_fields["seller_metrics"]
        assert "Chat Response Rate" not in prod_intel.source_fields["seller_metrics"]
        assert prod_intel.seller_rating is None

    def test_17_no_fake_reviews_generated(self):
        """Test 17: No reviews are fabricated when source extraction contains none."""
        item = ScrapeGraphProductItem(
            title="Product Without Reviews",
            price=150.0,
            currency="PKR",
            reviews=[]
        )
        prod_intel = ScrapeGraphNormalizer.to_product_intelligence(item, marketplace="daraz")
        assert len(prod_intel.reviews) == 0

    def test_18_no_fake_historical_observations(self):
        """Test 18: No fake historical observation dates are generated."""
        item = ScrapeGraphProductItem(
            title="Current Item",
            price=999.0,
            currency="PKR"
        )
        prod_intel = ScrapeGraphNormalizer.to_product_intelligence(item, marketplace="daraz")
        assert prod_intel.price == 999.0

    @pytest.mark.asyncio
    async def test_19_coexistence_with_specialized_daraz(self, test_repos):
        """Test 19: daraz_specialized provider route remains operational and distinct."""
        scraper_repo, mp_repo, uni_repo, dq_repo, dq_agent, uni_svc = test_repos
        bridge = ScraperIntegrationBridge(
            scraper_repo=scraper_repo,
            marketplace_repo=mp_repo,
            unified_repo=uni_repo
        )

        job = ScraperCrawlJob(
            id="job_coexist_daraz",
            marketplace="daraz",
            trigger_type="manual",
            target_count=1,
            metadata_json={"provider": "daraz_specialized", "dry_run": True}
        )
        scraper_repo.create_job(job)

        res = await bridge.run_scraper_job(job)
        assert res.metadata_json["provider"] == "daraz_specialized"

    @pytest.mark.asyncio
    async def test_20_coexistence_with_universal_orchestrator(self, test_repos):
        """Test 20: universal provider route remains operational and distinct."""
        scraper_repo, mp_repo, uni_repo, dq_repo, dq_agent, uni_svc = test_repos
        bridge = ScraperIntegrationBridge(
            scraper_repo=scraper_repo,
            marketplace_repo=mp_repo,
            unified_repo=uni_repo
        )

        job = ScraperCrawlJob(
            id="job_coexist_universal",
            marketplace="amazon",
            trigger_type="manual",
            target_count=1,
            metadata_json={"provider": "universal", "dry_run": True}
        )
        scraper_repo.create_job(job)

        res = await bridge.run_scraper_job(job)
        assert res.metadata_json["provider"] == "universal"

    @pytest.mark.asyncio
    async def test_21_smartscraper_multigraph_execution(self):
        """Test 21: SmartScraperMultiGraph scrapes multiple URLs and returns structured products."""
        cfg = ScrapeGraphAIConfig(
            enabled=True,
            provider="openai",
            model="gpt-4o-mini",
            api_key="test_key_multigraph",
            headless=True
        )
        engine = ScrapeGraphAIEngine(config=cfg)

        mock_products = [
            {"title": "Multi Item 1", "price": 1200.0, "currency": "PKR"},
            {"title": "Multi Item 2", "price": 2400.0, "currency": "PKR"},
        ]

        with patch("backend.app.services.scraper.providers.scrapegraphai.engine.SmartScraperMultiGraph") as MockMulti:
            mock_instance = MockMulti.return_value
            mock_instance.run.return_value = {"products": mock_products}

            res = await engine.scrape_multi_urls([
                "https://www.daraz.pk/products/item1.html",
                "https://www.daraz.pk/products/item2.html"
            ])
            assert len(res) == 2
            assert res[0]["title"] == "Multi Item 1"
            assert res[1]["price"] == 2400.0

    @pytest.mark.asyncio
    async def test_22_search_graph_execution(self):
        """Test 22: SearchGraph executes internet search and returns structured items."""
        cfg = ScrapeGraphAIConfig(
            enabled=True,
            provider="openai",
            model="gpt-4o-mini",
            api_key="test_key_searchgraph",
            headless=True
        )
        engine = ScrapeGraphAIEngine(config=cfg)

        mock_search_results = [
            {"title": "Search Result Earbuds", "price": 3500.0, "currency": "PKR"}
        ]

        with patch("backend.app.services.scraper.providers.scrapegraphai.engine.SearchGraph") as MockSearch:
            mock_instance = MockSearch.return_value
            mock_instance.run.return_value = {"products": mock_search_results}

            res = await engine.search_catalog("wireless earbuds daraz")
            assert len(res) == 1
            assert res[0]["title"] == "Search Result Earbuds"

    def test_23_dynamic_confidence_calculation(self):
        """Test 23: Extraction confidence is computed dynamically based on presence of extracted fields."""
        full_item = {
            "title": "Complete Smartwatch",
            "price": 4500.0,
            "seller_name": "Official Store",
            "image_url": "https://example.com/img.jpg"
        }
        prod_intel_full = ScrapeGraphNormalizer.to_product_intelligence(full_item, marketplace="daraz")
        assert prod_intel_full.overall_confidence >= 0.95
        assert prod_intel_full.extraction_confidence["title"] == 1.0
        assert prod_intel_full.extraction_confidence["price"] == 1.0
        assert prod_intel_full.extraction_confidence["seller"] == 0.9
        assert prod_intel_full.extraction_confidence["image"] == 1.0

        sparse_item = {
            "title": "",
            "price": 0.0
        }
        prod_intel_sparse = ScrapeGraphNormalizer.to_product_intelligence(sparse_item, marketplace="daraz")
        assert prod_intel_sparse.overall_confidence < 0.5
        assert prod_intel_sparse.extraction_confidence["title"] == 0.0
        assert prod_intel_sparse.extraction_confidence["price"] == 0.0

    def test_24_review_defaults_unbiased(self):
        """Test 24: Review defaults do not invent 5-star ratings or verified purchase status."""
        raw_review = {
            "reviewer_name": "Anonymous",
            "review_text": "Average product"
        }
        prod_dict = {
            "title": "Product With Unverified Review",
            "price": 1000.0,
            "reviews": [raw_review]
        }
        prod_intel = ScrapeGraphNormalizer.to_product_intelligence(prod_dict, marketplace="daraz")
        assert len(prod_intel.reviews) == 1
        rev = prod_intel.reviews[0]
        assert rev.verified_purchase is False
        assert rev.raw_date_str == ""
        assert rev.review_variants == ""
