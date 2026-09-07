import pytest
import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from backend.app.core.config import settings
from backend.app.models.domain import (
    ScraperCrawlJob, RawScrapedPayload, MarketplaceProduct,
    ProductMarketSnapshot, UnifiedProduct, ProductPlatformListing,
    DarazAuthSession, DarazProviderHealth
)
from backend.app.schemas.daraz import (
    DarazProductItem, DarazSearchResponse, DarazProductDetails
)
from backend.app.repositories.in_memory import (
    InMemoryScraperRepository, InMemoryMarketplaceProductRepository,
    InMemoryUnifiedProductRepository, InMemoryDataQualityRepository
)
from backend.app.services.scraper.bridge import ScraperIntegrationBridge
from backend.app.services.scraper.service import ScraperService
from backend.app.services.scraper.models import StartScraperJobRequest
from backend.app.services.daraz_service import DarazService
from backend.app.services.daraz.failover_pool import DarazFailoverPool
from backend.app.services.daraz.official_provider import DarazOfficialProvider
from backend.app.services.daraz.parse_scraper_provider import DarazParseScraperProvider
from backend.app.services.daraz.database_cache_provider import DarazDatabaseCacheProvider
from backend.app.services.daraz.base import DarazFetchResult
from backend.app.services.agents.data_quality.agent import DataQualityAgent
from backend.app.services.unified_intelligence_service import UnifiedProductIntelligenceService
from backend.app.api.deps import get_scraper_service, get_daraz_service


@pytest.fixture
def test_environment():
    scraper_repo = InMemoryScraperRepository()
    marketplace_repo = InMemoryMarketplaceProductRepository(storage_file=":memory:")
    unified_repo = InMemoryUnifiedProductRepository()
    dq_repo = InMemoryDataQualityRepository()
    dq_agent = DataQualityAgent(repository=dq_repo)

    unified_intel = UnifiedProductIntelligenceService(
        unified_repo=unified_repo,
        daraz_repo=marketplace_repo,
        data_quality_agent=dq_agent
    )

    failover_pool = DarazFailoverPool(repository=marketplace_repo)
    daraz_svc = DarazService(
        marketplace_repo=marketplace_repo,
        failover_pool=failover_pool
    )

    bridge = ScraperIntegrationBridge(
        scraper_repo=scraper_repo,
        marketplace_repo=marketplace_repo,
        unified_repo=unified_repo,
        unified_intelligence_svc=unified_intel,
        dq_agent=dq_agent,
        daraz_service=daraz_svc
    )

    service = ScraperService(
        scraper_repo=scraper_repo,
        marketplace_repo=marketplace_repo,
        unified_repo=unified_repo,
        bridge=bridge
    )

    return {
        "scraper_repo": scraper_repo,
        "marketplace_repo": marketplace_repo,
        "unified_repo": unified_repo,
        "dq_repo": dq_repo,
        "dq_agent": dq_agent,
        "unified_intel": unified_intel,
        "failover_pool": failover_pool,
        "daraz_svc": daraz_svc,
        "bridge": bridge,
        "service": service
    }


def test_dependency_injection_integrity(test_environment):
    """Verifies DarazService DI, bridge injection, and persistent repo sharing."""
    svc = test_environment["service"]
    bridge = test_environment["bridge"]
    daraz_svc = test_environment["daraz_svc"]

    assert bridge.daraz_service is not None
    assert bridge.daraz_service == daraz_svc
    assert bridge.daraz_service.marketplace_repo is not None
    assert bridge.daraz_service.failover_pool is not None
    assert len(bridge.daraz_service.failover_pool.providers) >= 4


def test_auth_session_persistence_and_leak_prevention(test_environment):
    """Verifies that OAuth sessions persist and secrets are never exposed."""
    marketplace_repo = test_environment["marketplace_repo"]
    official_prov = DarazOfficialProvider(
        app_key="test_app_key",
        app_secret="test_super_secret_key_12345",
        marketplace_repo=marketplace_repo
    )

    # 1. No token configured
    with patch.object(settings, "DARAZ_ACCESS_TOKEN", None):
        token, err = official_prov.get_active_token()
        assert token is None
        assert "authorization required" in err.lower()
        # Secret must never appear in error message
        assert "test_super_secret_key_12345" not in err

    # 2. Save active session in repository
    now = datetime.now(timezone.utc)
    sess = DarazAuthSession(
        id="daraz_sess_001",
        account="daraz_official_store",
        seller_id="seller_1001",
        country="pk",
        access_token="live_oauth_token_secret_xyz",
        refresh_token="live_refresh_token_secret_abc",
        expires_in=86400,
        status="authorized",
        authorized_at=now,
        created_at=now,
        updated_at=now
    )
    marketplace_repo.save_auth_session(sess)

    # 3. Official provider retrieves token from repo
    retrieved_token, err2 = official_prov.get_active_token()
    assert retrieved_token == "live_oauth_token_secret_xyz"
    assert err2 is None


def test_scenario_a_primary_provider_success(test_environment):
    """Scenario A: Primary provider succeeds; result returned without unnecessary fallback."""
    pool = test_environment["failover_pool"]
    p1 = pool.providers[0]

    mock_res = DarazFetchResult(
        success=True,
        data=DarazSearchResponse(
            query="earbuds",
            page=1,
            total_products=1,
            source="daraz_official_open_platform",
            products=[
                DarazProductItem(
                    platform="daraz",
                    product_id="111",
                    name="Primary Earbuds",
                    price=1500.0,
                    source="daraz_official_open_platform"
                )
            ]
        ),
        provider_name="daraz_official_open_platform"
    )

    with patch.object(p1, "search_products", return_value=mock_res):
        res = pool.execute_with_failover("search_products", query="earbuds")
        assert res.success is True
        assert res.provider_name == "daraz_official_open_platform"
        assert len(res.data.products) == 1


def test_scenario_b_primary_provider_timeout_failover(test_environment):
    """Scenario B: Primary provider times out; fails over to next provider successfully."""
    pool = test_environment["failover_pool"]
    p1 = pool.providers[0]
    p2 = pool.providers[1]

    p1_fail = DarazFetchResult(
        success=False,
        error_code=504,
        error_message="Gateway Timeout",
        provider_name=p1.name
    )
    p2_success = DarazFetchResult(
        success=True,
        data=DarazSearchResponse(
            query="earbuds",
            page=1,
            total_products=1,
            source="parse_daraz_api",
            products=[
                DarazProductItem(
                    platform="daraz",
                    product_id="222",
                    name="Fallback Earbuds",
                    price=1800.0,
                    source="parse_daraz_api"
                )
            ]
        ),
        provider_name=p2.name
    )

    with patch.object(p1, "search_products", return_value=p1_fail), \
         patch.object(p2, "search_products", return_value=p2_success):
        res = pool.execute_with_failover("search_products", query="earbuds")
        assert res.success is True
        assert res.provider_name == p2.name
        assert len(res.data.products) == 1
        assert res.data.products[0].product_id == "222"


def test_scenario_c_primary_zero_products_failover(test_environment):
    """Scenario C: Primary returns 0 products; failover policy and bridge handle cleanly without fake data."""
    bridge = test_environment["bridge"]
    scraper_repo = test_environment["scraper_repo"]
    marketplace_repo = test_environment["marketplace_repo"]

    # Seed 1 real cached item in database
    now = datetime.now(timezone.utc)
    cached_prod = MarketplaceProduct(
        id="daraz_333",
        platform="daraz",
        product_id="333",
        product_name="Wireless Earbuds Bluetooth 5.0 Headset",
        price=1200.0,
        original_price=1500.0,
        discount_percentage=20.0,
        currency="PKR",
        rating=4.5,
        review_count=10,
        stock_status="in_stock",
        in_stock=True,
        first_seen_at=now,
        last_seen_at=now,
        last_synced_at=now,
        raw_source_data={"source_provider": "database_cache"},
        created_at=now,
        updated_at=now
    )
    marketplace_repo.upsert_product(cached_prod)

    job = ScraperCrawlJob(
        id="job_zero_test_01",
        marketplace="daraz",
        trigger_type="manual",
        keywords=["wireless earbuds"],
        target_count=1,
        max_workers=1,
        status="queued",
        metadata_json={"provider": "auto"},
        created_at=now,
        updated_at=now
    )
    scraper_repo.create_job(job)

    # Specialized engine returns 0 items (e.g. empty search result)
    async def mock_run_pipeline(*args, **kwargs):
        return {"items_extracted": 0, "challenged_count": 0, "failed_count": 0}

    with patch.object(bridge.daraz_specialized_engine, "run_daraz_crawl_pipeline", side_effect=mock_run_pipeline), \
         patch.object(bridge.daraz_service, "_execute_request", side_effect=RuntimeError("Parse upstream offline")):
        completed_job = asyncio.run(bridge.run_scraper_job(job))
        assert completed_job.status == "completed"
        assert completed_job.products_persisted >= 1


def test_scenario_d_all_providers_fail(test_environment):
    """Scenario D: All providers fail; job becomes failed with sanitized diagnostic, never hangs."""
    bridge = test_environment["bridge"]
    scraper_repo = test_environment["scraper_repo"]

    now = datetime.now(timezone.utc)
    job = ScraperCrawlJob(
        id="job_fail_all_01",
        marketplace="daraz",
        trigger_type="manual",
        keywords=["nonexistent product query xyz"],
        target_count=5,
        max_workers=1,
        status="queued",
        metadata_json={"provider": "auto"},
        created_at=now,
        updated_at=now
    )
    scraper_repo.create_job(job)

    async def mock_failing_pipeline(*args, **kwargs):
        raise RuntimeError("Network unreachable / upstream connection refused")

    def mock_failing_daraz_search(*args, **kwargs):
        raise RuntimeError("Daraz API upstream down")

    with patch.object(bridge.daraz_specialized_engine, "run_daraz_crawl_pipeline", side_effect=mock_failing_pipeline), \
         patch.object(bridge.daraz_service, "search_products", side_effect=mock_failing_daraz_search), \
         patch("backend.app.services.scraper.bridge.ProductionScrapingOrchestrator.execute_crawl", side_effect=mock_failing_pipeline):
        completed_job = asyncio.run(bridge.run_scraper_job(job))
        assert completed_job.status == "failed"
        assert completed_job.products_persisted == 0
        assert "Network unreachable" in completed_job.error_message or "upstream" in completed_job.error_message


def test_scenario_e_auth_unavailable_clean_fallback(test_environment):
    """Scenario E: Auth missing on P1; cleanly attempts fallback without crash or credential leak."""
    pool = test_environment["failover_pool"]
    p1 = pool.providers[0]  # Official provider (unauthenticated)
    p2 = pool.providers[1]  # Parse scraper provider

    p1_auth_fail = DarazFetchResult(
        success=False,
        error_code=401,
        error_message="AUTHENTICATION_UNAVAILABLE: Daraz OAuth authorization required.",
        provider_name=p1.name
    )

    p2_result = DarazFetchResult(
        success=True,
        data=DarazSearchResponse(
            query="earbuds",
            page=1,
            total_products=1,
            source="parse_daraz_api",
            products=[
                DarazProductItem(
                    platform="daraz",
                    product_id="555",
                    name="Unauthenticated Fallback Product",
                    price=999.0,
                    source="parse_daraz_api"
                )
            ]
        ),
        provider_name=p2.name
    )

    with patch.object(p1, "search_products", return_value=p1_auth_fail), \
         patch.object(p2, "search_products", return_value=p2_result):
        res = pool.execute_with_failover("search_products", query="earbuds")
        assert res.success is True
        assert res.provider_name == p2.name
        assert len(res.data.products) == 1


def test_scenario_f_anti_bot_challenge_handling(test_environment):
    """Scenario F: Anti-bot challenge occurs; bounded challenge handling without crashing or hanging."""
    bridge = test_environment["bridge"]
    scraper_repo = test_environment["scraper_repo"]

    now = datetime.now(timezone.utc)
    job = ScraperCrawlJob(
        id="job_challenge_test_01",
        marketplace="daraz",
        trigger_type="manual",
        keywords=["earbuds"],
        target_count=3,
        max_workers=1,
        status="queued",
        metadata_json={"provider": "daraz_specialized"},
        created_at=now,
        updated_at=now
    )
    scraper_repo.create_job(job)

    async def mock_challenged_pipeline(*args, **kwargs):
        return {"items_extracted": 0, "challenged_count": 1, "failed_count": 0}

    with patch.object(bridge.daraz_specialized_engine, "run_daraz_crawl_pipeline", side_effect=mock_challenged_pipeline):
        completed_job = asyncio.run(bridge.run_scraper_job(job))
        assert completed_job.challenged_count == 1
        assert completed_job.status in ("completed", "failed")


def test_failover_source_provenance_integrity(test_environment):
    """Verifies that RawScrapedPayload, MarketplaceProduct, and ProductPlatformListing record the true source provider."""
    bridge = test_environment["bridge"]
    scraper_repo = test_environment["scraper_repo"]
    marketplace_repo = test_environment["marketplace_repo"]
    unified_repo = test_environment["unified_repo"]

    now = datetime.now(timezone.utc)
    job = ScraperCrawlJob(
        id="job_provenance_001",
        marketplace="daraz",
        trigger_type="manual",
        keywords=["earbuds"],
        target_count=1,
        max_workers=1,
        status="queued",
        metadata_json={"provider": "auto"},
        created_at=now,
        updated_at=now
    )
    scraper_repo.create_job(job)

    # Simulate specialized engine yielding 1 product tagged as 'daraz_specialized'
    async def mock_pipeline(keywords, urls, max_products, max_review_pages, item_callback, is_cancelled_callback):
        await item_callback({
            "product_id": "prov_item_777",
            "title": "Specialized Wireless Earbuds",
            "price": 2500.0,
            "original_price": 3000.0,
            "discount": 16.7,
            "currency": "PKR",
            "rating": 4.8,
            "review_count": 50,
            "in_stock": True,
            "source_provider": "daraz_specialized"
        })
        return {"items_extracted": 1, "challenged_count": 0, "failed_count": 0}

    with patch.object(bridge.daraz_specialized_engine, "run_daraz_crawl_pipeline", side_effect=mock_pipeline):
        completed_job = asyncio.run(bridge.run_scraper_job(job))
        assert completed_job.products_persisted == 1

    # Check RawScrapedPayload
    raw_items = scraper_repo.list_raw_payloads(crawl_job_id="job_provenance_001")
    assert len(raw_items) == 1
    assert raw_items[0].raw_payload.get("source_provider") == "daraz_specialized"

    # Check MarketplaceProduct
    mp = marketplace_repo.get_product(platform="daraz", product_id="prov_item_777")
    assert mp is not None
    assert mp.raw_source_data.get("source_provider") == "daraz_specialized"

    # Check ProductPlatformListing
    listing = unified_repo.get_platform_listing(platform="daraz", platform_product_id="prov_item_777")
    assert listing is not None
    assert listing.source_provider == "daraz_specialized"


def test_background_task_lifecycle_and_cleanup(test_environment):
    """Verifies that ScraperService starts, tracks, and cleans up active asyncio tasks upon completion."""
    service = test_environment["service"]
    scraper_repo = test_environment["scraper_repo"]

    req = StartScraperJobRequest(
        marketplace="daraz",
        keyword="wireless earbuds",
        max_products=1,
        dry_run=True
    )

    # Run async start_job
    progress = asyncio.run(service.start_job(req))
    job_id = progress.job_id
    assert job_id is not None

    # Retrieve and verify job status
    status_resp = service.get_job_status(job_id)
    assert status_resp is not None
    assert status_resp.status in ("queued", "running", "completed")

    # Stop job and verify cancellation cleanup
    stop_ok = service.stop_job(job_id)
    assert stop_ok is True
    stopped_job = scraper_repo.get_job(job_id)
    assert stopped_job.status in ("stopped", "cancelled")
    assert job_id not in ScraperService._active_tasks
