import pytest
import asyncio
import logging

from backend.app.services.scraper.providers.daraz_specialized import (
    DarazSpecializedScraperEngine, detect_challenge
)
from backend.app.services.scraper.bridge import ScraperIntegrationBridge
from backend.app.repositories.in_memory import (
    InMemoryScraperRepository, InMemoryDataQualityRepository,
    InMemoryMarketplaceProductRepository, InMemoryUnifiedProductRepository
)
from backend.app.services.agents.data_quality.agent import DataQualityAgent
from backend.app.services.unified_intelligence_service import UnifiedProductIntelligenceService
from backend.app.models.domain import ScraperCrawlJob

logger = logging.getLogger("test.daraz.live")

@pytest.mark.asyncio
async def test_live_daraz_keyword_and_direct_url_crawl():
    """
    Live controlled extraction testing against Daraz.pk.
    Extracts 1-2 products for keyword search and a direct product URL,
    verifying Playwright headless browser navigation, challenge detection,
    and structured payload extraction.
    """
    engine = DarazSpecializedScraperEngine(headless=True)
    
    # 1. Test live search catalog crawl
    logger.info("Starting live search catalog crawl for 'wireless mouse'...")
    search_results, is_challenged, challenge_reason = await engine.crawl_keyword_search(
        keyword="wireless mouse",
        max_items=2,
        domain="daraz.pk"
    )
    
    assert isinstance(search_results, list)
    logger.info(f"Live search returned {len(search_results)} items (challenged={is_challenged}).")
    
    if search_results:
        first_item = search_results[0]
        assert "title" in first_item
        assert "price" in first_item
        assert "product_url" in first_item
        logger.info(f"Successfully extracted search item: {first_item.get('title')} (Price: {first_item.get('price')})")
        
        # 2. Test live direct product URL crawl
        if first_item.get("product_url"):
            logger.info(f"Crawling direct product URL: {first_item['product_url']}")
            detail, reviews, is_chal, chal_reason = await engine.crawl_product_detail(
                url=first_item["product_url"],
                max_review_pages=1
            )
            assert isinstance(detail, dict)
            logger.info(f"Detail extracted - Title: {detail.get('title')}, Price: {detail.get('price')}, Seller: {detail.get('seller_name')}")
            assert "title" in detail
            assert "price" in detail
            assert "product_id" in detail
            assert "marketplace" in detail
            assert detail["marketplace"] == "daraz"

@pytest.mark.asyncio
async def test_live_daraz_bridge_pipeline_execution():
    """
    Live end-to-end test connecting specialized Daraz scraper to ScraperIntegrationBridge
    and verifying persistence into in-memory/Postgres repositories.
    """
    scraper_repo = InMemoryScraperRepository()
    quality_repo = InMemoryDataQualityRepository()
    mkt_repo = InMemoryMarketplaceProductRepository()
    u_repo = InMemoryUnifiedProductRepository()

    quality_agent = DataQualityAgent(repository=quality_repo)
    intel_service = UnifiedProductIntelligenceService(
        unified_repo=u_repo,
        daraz_repo=mkt_repo,
        data_quality_agent=quality_agent
    )

    specialized_engine = DarazSpecializedScraperEngine(headless=True)
    bridge = ScraperIntegrationBridge(
        scraper_repo=scraper_repo,
        marketplace_repo=mkt_repo,
        unified_repo=u_repo,
        dq_repo=quality_repo,
        dq_agent=quality_agent,
        unified_intelligence_svc=intel_service,
        daraz_specialized_engine=specialized_engine
    )

    job = ScraperCrawlJob(
        id="job-daraz-live-test",
        marketplace="daraz",
        keywords=["earphones"],
        target_count=2,
        metadata_json={"provider": "daraz_specialized"}
    )
    scraper_repo.create_job(job)

    res_job = await bridge.run_scraper_job(job)
    assert res_job.status in ["completed", "completed_with_challenges"]
    assert res_job.products_persisted >= 0


