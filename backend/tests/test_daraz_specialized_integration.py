import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.domain import (
    ScraperCrawlJob, RawScrapedPayload, MarketplaceProduct, ProductMarketSnapshot,
    DarazSeller, DarazReview, UnifiedProduct
)
from backend.app.repositories.in_memory import (
    InMemoryScraperRepository, InMemoryMarketplaceProductRepository,
    InMemoryUnifiedProductRepository, InMemoryDataQualityRepository
)
from backend.app.services.scraper.bridge import ScraperIntegrationBridge
from backend.app.services.scraper.service import ScraperService
from backend.app.services.scraper.providers.daraz_specialized import (
    DarazSpecializedScraperEngine, detect_challenge,
    parse_page_data_json, extract_products_from_json, parse_dom_item,
    extract_product_details, extract_product_reviews, extract_variations
)
from backend.app.services.agents.data_quality.agent import DataQualityAgent
from backend.app.services.unified_intelligence_service import UnifiedProductIntelligenceService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def repos():
    scraper_repo = InMemoryScraperRepository()
    marketplace_repo = InMemoryMarketplaceProductRepository()
    unified_repo = InMemoryUnifiedProductRepository()
    dq_repo = InMemoryDataQualityRepository()
    dq_agent = DataQualityAgent(repository=dq_repo)
    unified_intel = UnifiedProductIntelligenceService(
        unified_repo=unified_repo,
        daraz_repo=marketplace_repo,
        data_quality_agent=dq_agent
    )
    bridge = ScraperIntegrationBridge(
        scraper_repo=scraper_repo,
        marketplace_repo=marketplace_repo,
        unified_repo=unified_repo,
        dq_repo=dq_repo,
        unified_intelligence_svc=unified_intel,
        dq_agent=dq_agent
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
        "bridge": bridge,
        "service": service,
        "unified_intel": unified_intel
    }


def test_01_catalog_parser_json():
    """Verify window.pageData extraction for Daraz search."""
    sample_script = """
    <script>
    window.pageData={"mods":{"listItems":[
        {
            "name":"Logitech MX Master 3S Wireless Mouse",
            "priceShow":"Rs. 24,999",
            "originalPrice":"Rs. 29,999",
            "discount":"-17%",
            "ratingScore":"4.9",
            "review":"342",
            "location":"Islamabad",
            "brandName":"Logitech",
            "productUrl":"//www.daraz.pk/products/logitech-mx-master-3s-i123456.html",
            "image":"//img.daraz.pk/p/mx3s.jpg",
            "itemId":"123456"
        }
    ]}};
    </script>
    """
    page_data = parse_page_data_json(sample_script)
    assert page_data is not None
    assert "mods" in page_data

    products = extract_products_from_json(page_data, domain="daraz.pk")
    assert len(products) == 1
    p = products[0]
    assert p["title"] == "Logitech MX Master 3S Wireless Mouse"
    assert p["price"] == 24999.0
    assert p["original_price"] == 29999.0
    assert p["discount"] == 17.0
    assert p["rating"] == 4.9
    assert p["review_count"] == 342
    assert p["brand"] == "Logitech"
    assert p["product_url"] == "https://www.daraz.pk/products/logitech-mx-master-3s-i123456.html"
    assert p["image_url"] == "https://img.daraz.pk/p/mx3s.jpg"


def test_02_catalog_dom_item_fallback():
    """Verify DOM item fallback parser for Daraz catalog search cards."""
    from bs4 import BeautifulSoup
    html = """
    <div class="gridItem">
        <div class="RfADt"><a title="Redragon K552 RGB Keyboard" href="//www.daraz.pk/products/k552-i9988.html">Redragon K552 RGB Keyboard</a></div>
        <div class="ooOxS">Rs. 7,499</div>
        <div class="IcOsH">-25% Off</div>
        <div class="mdmmT"><i class="Dy1nx"></i><i class="Dy1nx"></i><i class="Dy1nx"></i><i class="Dy1nx"></i><i class="Dy1nx"></i></div>
        <div class="qzqFw">(85)</div>
        <div class="oa6ri" title="Lahore">Lahore</div>
        <img src="//img.daraz.pk/p/k552.jpg" />
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    item = soup.select_one(".gridItem")
    prod = parse_dom_item(item, domain="daraz.pk", idx=1)

    assert prod["title"] == "Redragon K552 RGB Keyboard"
    assert prod["price"] == 7499.0
    assert prod["discount"] == 25.0
    assert prod["rating"] == 5.0
    assert prod["review_count"] == 85
    assert prod["location"] == "Lahore"
    assert prod["product_url"] == "https://www.daraz.pk/products/k552-i9988.html"
    assert prod["image_url"] == "https://img.daraz.pk/p/k552.jpg"


@pytest.mark.asyncio
async def test_03_bridge_specialized_daraz_full_pipeline_persistence(repos):
    """
    Verify complete 20-point extraction & persistence pipeline:
    - ScraperIntegrationBridge converts specialized Daraz data
    - DataQualityAgent validates payload
    - RawScrapedPayload persisted
    - MarketplaceProduct persisted
    - ProductMarketSnapshot recorded
    - DarazSeller and DarazReview persisted
    - UnifiedProduct catalog linked
    """
    bridge = repos["bridge"]
    scraper_repo = repos["scraper_repo"]
    marketplace_repo = repos["marketplace_repo"]
    unified_repo = repos["unified_repo"]

    specialized_daraz_payload = {
        "product_id": "439281729",
        "sku": "SKU-439281729",
        "url": "https://www.daraz.pk/products/redragon-k552-i439281729.html",
        "title": "Redragon K552 Mechanical Gaming Keyboard RGB Backlit",
        "description": "Compact 87-key space-saving design with custom mechanical switches.",
        "price": 7499.0,
        "original_price": 9999.0,
        "discount": 25.0,
        "discount_label": "25% Off",
        "currency": "PKR",
        "brand": "Redragon",
        "category": "Computers & Laptops > Computer Accessories > Keyboards",
        "rating": 4.8,
        "review_count": 142,
        "sold_count": 500,
        "in_stock": True,
        "seller_name": "TechZone Official",
        "seller_id": "techzone-pk",
        "seller_url": "https://www.daraz.pk/shop/techzone-pk",
        "seller_metrics": {
            "Positive Seller Ratings": "96%",
            "Ship on Time": "99%",
            "Chat Response Rate": "95%"
        },
        "image_url": "https://img.daraz.pk/p/keyboard_front.jpg",
        "images": [
            "https://img.daraz.pk/p/keyboard_front.jpg",
            "https://img.daraz.pk/p/keyboard_side.jpg"
        ],
        "variations": [
            {"sku_id": "var_red", "name": "Red Switch / Black", "in_stock": True},
            {"sku_id": "var_blue", "name": "Blue Switch / Black", "in_stock": True}
        ],
        "specifications": {
            "Key Switches": "Outemu Blue / Red",
            "Backlight": "RGB Rainbow",
            "Connection": "USB Wired"
        },
        "reviews": [
            {
                "page": 1,
                "review_id": "rev_001",
                "reviewer_name": "Zubair A.",
                "rating": 5.0,
                "date_str": "14 Aug 2026",
                "variation": "Red Switch / Black",
                "content": "Authentic product, clicky switches are responsive.",
                "review_text": "Authentic product, clicky switches are responsive.",
                "images": ["https://img.daraz.pk/review1.jpg"],
                "verified_purchase": True
            }
        ]
    }

    job = ScraperCrawlJob(
        id="job_daraz_specialized_test",
        marketplace="daraz",
        target_count=1,
        status="running"
    )
    scraper_repo.create_job(job)

    # Convert to ProductIntelligence and Persist
    prod_intel = bridge._specialized_dict_to_product_intelligence(specialized_daraz_payload)
    await bridge._persist_scraped_product(prod_intel, job)

    assert job.products_persisted == 1

    # 1. Verify RawScrapedPayload
    raw = scraper_repo.get_raw_payload("daraz", "439281729")
    assert raw is not None
    assert raw.quality_status == "valid"
    assert raw.raw_payload["title"] == "Redragon K552 Mechanical Gaming Keyboard RGB Backlit"
    assert raw.raw_payload["specifications"]["Key Switches"] == "Outemu Blue / Red"

    # 2. Verify MarketplaceProduct
    mp = marketplace_repo.get_product("daraz", "439281729")
    assert mp is not None
    assert mp.price == 7499.0
    assert mp.original_price == 9999.0
    assert mp.discount_percentage == 25.0
    assert mp.rating == 4.8
    assert mp.review_count == 142
    assert mp.seller_name == "TechZone Official"
    assert mp.category == "Computers & Laptops > Computer Accessories > Keyboards"
    assert mp.in_stock is True

    # 3. Verify ProductMarketSnapshot
    snapshots = marketplace_repo.get_snapshots("daraz", "439281729")
    assert len(snapshots) >= 1
    assert snapshots[0].price == 7499.0

    # 4. Verify DarazSeller
    seller = marketplace_repo.get_seller("techzone-pk")
    assert seller is not None
    assert seller.seller_name == "TechZone Official"

    # 5. Verify DarazReview
    reviews = marketplace_repo.list_reviews("439281729")
    assert len(reviews) >= 1
    assert reviews[0].reviewer_name == "Zubair A."
    assert reviews[0].rating == 5.0

    # 6. Verify UnifiedProduct linking
    unified_list = unified_repo.list_unified_products(limit=10)
    assert len(unified_list) >= 1


def test_04_scraper_api_retrieval_and_details(repos, client):
    """Verify frontend/API retrieval of scraped product, raw data, and history."""
    service = repos["service"]
    marketplace_repo = repos["marketplace_repo"]
    scraper_repo = repos["scraper_repo"]

    now = datetime.now(timezone.utc)
    # Seed a product
    mp = MarketplaceProduct(
        id="daraz_991122",
        platform="daraz",
        product_id="991122",
        product_name="Baseus GaN 65W Fast Charger",
        product_url="https://www.daraz.pk/products/baseus-gan-65w-i991122.html",
        image_url="https://img.daraz.pk/p/baseus65w.jpg",
        seller_name="Baseus Official Store",
        seller_id="baseus-pk",
        category="Mobile Accessories > Chargers",
        price=4500.0,
        original_price=6000.0,
        discount_percentage=25.0,
        discount_label="25% Off",
        rating=4.9,
        review_count=98,
        in_stock=True,
        currency="PKR",
        location="Pakistan",
        raw_source_data={"specifications": {"Wattage": "65W", "Ports": "3-Port Type-C + USB"}},
        first_seen_at=now,
        last_seen_at=now,
        last_synced_at=now,
        created_at=now,
        updated_at=now
    )
    marketplace_repo.upsert_product(mp)

    raw = RawScrapedPayload(
        id="raw_daraz_991122",
        marketplace="daraz",
        product_id="991122",
        source_url="https://www.daraz.pk/products/baseus-gan-65w-i991122.html",
        raw_payload={"title": "Baseus GaN 65W Fast Charger", "price": 4500.0, "specifications": {"Wattage": "65W"}},
        normalized_payload={"title": "Baseus GaN 65W Fast Charger", "price": 4500.0},
        scraped_at=now,
        created_at=now
    )
    scraper_repo.save_raw_payload(raw)

    snap = ProductMarketSnapshot(
        id="snap_991122_1",
        product_id="991122",
        platform="daraz",
        price=4500.0,
        original_price=6000.0,
        discount=25.0,
        rating=4.9,
        review_count=98,
        stock_status="in_stock",
        observed_at=now,
        created_at=now
    )
    marketplace_repo.batch_create_snapshots([snap])

    # Test ScraperService queries
    prod = service.get_product("991122", marketplace="daraz")
    assert prod is not None
    assert prod.title == "Baseus GaN 65W Fast Charger"
    assert prod.specifications["Wattage"] == "65W"

    raw_res = service.get_raw_payload("991122", marketplace="daraz")
    assert raw_res is not None
    assert raw_res.raw_payload["specifications"]["Wattage"] == "65W"

    hist_res = service.get_product_history("991122", marketplace="daraz")
    assert hist_res.total_snapshots >= 1
    assert hist_res.snapshots[0].price == 4500.0
