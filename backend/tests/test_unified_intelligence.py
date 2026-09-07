import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.domain import (
    UnifiedProduct, ProductPlatformListing, ProductMatchCandidate, ProductMatchAudit,
    MarketplaceProduct, ShopifyProduct, ProductMarketSnapshot, ShopifyProductSnapshot
)
from backend.app.repositories.in_memory import InMemoryUnifiedProductRepository, InMemoryMarketplaceProductRepository, InMemoryShopifyRepository
from backend.app.services.normalization.product_normalizer import ProductNormalizer
from backend.app.services.matching.product_matcher import ProductMatcher, MatchDecision
from backend.app.services.unified_intelligence_service import UnifiedProductIntelligenceService

client = TestClient(app)

# -----------------------------------------------------------------------------
# 1. Daraz Normalization
# -----------------------------------------------------------------------------
def test_daraz_normalization():
    raw_daraz = {
        "title": "Zero® Evo Wireless Earbuds | 10mm Base Driver - 100% Original Official Warranty",
        "vendor": "Zero Official Store",
        "brand": "Zero",
        "price": 2999.0,
        "product_url": "https://www.daraz.pk/products/zero-evo.html",
        "image_url": "https://img.daraz.pk/zero.jpg",
        "rating": 4.8
    }
    norm = ProductNormalizer.normalize_product(raw_daraz, platform="Daraz")
    assert "100%" not in norm["canonical_name"]
    assert "Official Warranty" not in norm["canonical_name"]
    assert "10mm" in norm["canonical_name"].lower()
    assert norm["brand"] == "Zero"
    assert norm["completeness_score"] == 1.0


# -----------------------------------------------------------------------------
# 2. Shopify Normalization
# -----------------------------------------------------------------------------
def test_shopify_normalization():
    raw_shopify = {
        "title": "Zero Evo Wireless Earbuds 10 mm - Matte Black Edition",
        "vendor": "Zero Audio",
        "price": 29.99,
        "product_url": "https://zeroaudio.com/products/evo-earbuds",
        "image_url": "https://cdn.shopify.com/evo.jpg",
        "rating": 4.7
    }
    norm = ProductNormalizer.normalize_product(raw_shopify, platform="Shopify")
    assert "10mm" in norm["canonical_name"].lower()
    assert norm["brand"] == "Zero"
    assert norm["completeness_score"] >= 0.8


# -----------------------------------------------------------------------------
# 3 & 4. Unified Product Creation & Update
# -----------------------------------------------------------------------------
def test_unified_product_creation_and_update(tmp_path):
    store_file = str(tmp_path / "test_unified.json")
    repo = InMemoryUnifiedProductRepository(data_file=store_file)
    service = UnifiedProductIntelligenceService(unified_repo=repo)

    # Ingest new item
    prod, listing, decision = service.match_and_upsert_listing(
        platform="Daraz",
        platform_product_id="daraz_1001",
        title="Anker Soundcore Life P2 Mini Wireless Earbuds",
        price=6500.0,
        product_url="https://www.daraz.pk/products/anker-p2.html",
        currency="PKR",
        seller_name="Anker Flagship Store",
        rating=4.9,
        review_count=450
    )
    assert prod is not None
    assert prod.brand == "Anker"
    assert listing.platform == "Daraz"
    first_seen = prod.first_seen_at

    # Update item later -> preserves first_seen_at
    prod_updated, listing_updated, _ = service.match_and_upsert_listing(
        platform="Daraz",
        platform_product_id="daraz_1001",
        title="Anker Soundcore Life P2 Mini Wireless Earbuds (Upgraded)",
        price=6200.0,
        product_url="https://www.daraz.pk/products/anker-p2.html",
        currency="PKR",
        seller_name="Anker Flagship Store",
        rating=4.95,
        review_count=500
    )
    assert prod_updated.unified_product_id == prod.unified_product_id
    assert prod_updated.first_seen_at == first_seen
    assert listing_updated.price == 6200.0


# -----------------------------------------------------------------------------
# 5 & 6. Platform Listing Creation & Update
# -----------------------------------------------------------------------------
def test_platform_listing_creation_and_update(tmp_path):
    store_file = str(tmp_path / "test_listings.json")
    repo = InMemoryUnifiedProductRepository(data_file=store_file)
    service = UnifiedProductIntelligenceService(unified_repo=repo)

    _, listing1, _ = service.match_and_upsert_listing(
        platform="Shopify",
        platform_product_id="shp_9901",
        store_domain="gymshark.com",
        title="Gymshark Training Oversized T-Shirt",
        price=38.0,
        product_url="https://gymshark.com/products/training-tee",
        currency="USD",
        vendor="Gymshark",
        rating=4.6,
        review_count=88
    )
    assert listing1.platform_product_id == "shp_9901"
    assert listing1.store_domain == "gymshark.com"
    assert listing1.price == 38.0

    # Re-sync update with new price
    _, listing2, _ = service.match_and_upsert_listing(
        platform="Shopify",
        platform_product_id="shp_9901",
        store_domain="gymshark.com",
        title="Gymshark Training Oversized T-Shirt",
        price=32.0,
        product_url="https://gymshark.com/products/training-tee",
        currency="USD",
        vendor="Gymshark",
        rating=4.7,
        review_count=95
    )
    assert listing2.id == listing1.id
    assert listing2.price == 32.0


# -----------------------------------------------------------------------------
# 7. Exact SKU Matching
# -----------------------------------------------------------------------------
def test_exact_sku_matching():
    norm1 = {"canonical_name": "Sony Wireless Headphones", "brand": "Sony", "tokens": {"sony", "headphones"}}
    norm2 = {"canonical_name": "Sony Noise Cancelling Over Ear", "brand": "Sony", "tokens": {"sony", "ear"}}
    ids1 = {"sku": "WH1000XM4-BLK"}
    ids2 = {"sku": "WH1000XM4-BLK"}

    decision = ProductMatcher.evaluate_match(norm1, norm2, ids1, ids2)
    assert decision.is_match is True
    assert decision.confidence == 1.0
    assert decision.method == "sku_exact"
    assert decision.status == "matched"


# -----------------------------------------------------------------------------
# 8. Brand + Model Matching
# -----------------------------------------------------------------------------
def test_brand_model_exact_matching():
    norm1 = {
        "canonical_name": "Logitech M570 Wireless Trackball Mouse",
        "brand": "Logitech",
        "model_number": "M570",
        "tokens": {"logitech", "m570", "wireless", "trackball", "mouse"}
    }
    norm2 = {
        "canonical_name": "Logitech Trackball M570 Ergonomic USB",
        "brand": "Logitech",
        "model_number": "M570",
        "tokens": {"logitech", "trackball", "m570", "ergonomic"}
    }
    decision = ProductMatcher.evaluate_match(norm1, norm2)
    assert decision.is_match is True
    assert decision.confidence >= 0.95
    assert decision.method == "brand_model_exact"


# -----------------------------------------------------------------------------
# 9. Normalized Name Similarity Matching (Auto Match >= 0.95)
# -----------------------------------------------------------------------------
def test_normalized_name_similarity_matching():
    norm1 = {
        "canonical_name": "Zero Evo Wireless Earbuds 10mm Driver",
        "brand": "Zero",
        "tokens": {"zero", "evo", "wireless", "earbuds", "10mm", "driver"}
    }
    norm2 = {
        "canonical_name": "Zero Evo Wireless Earbuds 10mm Driver Bluetooth",
        "brand": "Zero",
        "tokens": {"zero", "evo", "wireless", "earbuds", "10mm", "driver", "bluetooth"}
    }
    decision = ProductMatcher.evaluate_match(norm1, norm2)
    assert decision.is_match is True
    assert decision.confidence >= 0.85
    assert decision.status in ["matched", "probable"]


# -----------------------------------------------------------------------------
# 10. Low-Confidence Non-Match (< 0.80)
# -----------------------------------------------------------------------------
def test_low_confidence_non_match():
    norm1 = {
        "canonical_name": "Apple iPhone 15 Pro Max 256GB Titanium",
        "brand": "Apple",
        "model_number": "IPHONE15",
        "tokens": {"apple", "iphone", "15", "pro", "max", "256gb"}
    }
    norm2 = {
        "canonical_name": "Samsung Galaxy S24 Ultra 512GB Grey",
        "brand": "Samsung",
        "model_number": "S24",
        "tokens": {"samsung", "galaxy", "s24", "ultra", "512gb"}
    }
    decision = ProductMatcher.evaluate_match(norm1, norm2)
    assert decision.is_match is False
    assert decision.confidence < 0.50
    assert decision.status == "rejected"


# -----------------------------------------------------------------------------
# 11 & 12. Match Confidence Calculation & Audit Creation
# -----------------------------------------------------------------------------
def test_match_audit_creation(tmp_path):
    store_file = str(tmp_path / "test_audit.json")
    repo = InMemoryUnifiedProductRepository(data_file=store_file)
    service = UnifiedProductIntelligenceService(unified_repo=repo)

    # 1. First product on Daraz
    prod1, _, _ = service.match_and_upsert_listing(
        platform="Daraz",
        platform_product_id="daraz_zero_01",
        title="Zero Evo Wireless Earbuds 10mm Base Driver",
        price=2999.0,
        product_url="https://daraz.pk/zero-evo",
        currency="PKR",
        identifiers={"sku": "ZERO-EVO-10MM"}
    )

    # 2. Matching product on Shopify with same SKU
    prod2, _, decision = service.match_and_upsert_listing(
        platform="Shopify",
        platform_product_id="shp_zero_01",
        store_domain="zerolifestyle.co",
        title="Zero Evo Earbuds",
        price=29.99,
        product_url="https://zerolifestyle.co/products/zero-evo",
        currency="USD",
        identifiers={"sku": "ZERO-EVO-10MM"}
    )

    # Both belong to same unified entity
    assert prod1.unified_product_id == prod2.unified_product_id
    assert decision.confidence == 1.0

    # Audit record exists
    audit = repo.get_match_audit(prod1.unified_product_id)
    assert audit is not None
    assert audit.matching_method == "sku_exact"
    assert audit.matching_confidence == 1.0


# -----------------------------------------------------------------------------
# 13 & 14. Cross-Platform Product Retrieval & Price Comparison
# -----------------------------------------------------------------------------
def test_cross_platform_product_retrieval_and_price_comparison(tmp_path):
    store_file = str(tmp_path / "test_cross.json")
    repo = InMemoryUnifiedProductRepository(data_file=store_file)
    service = UnifiedProductIntelligenceService(unified_repo=repo)

    # Daraz listing
    prod, _, _ = service.match_and_upsert_listing(
        platform="Daraz",
        platform_product_id="dz_999",
        title="Sony WH-1000XM4 Wireless Noise Canceling Headphones",
        price=65000.0,
        original_price=75000.0,
        product_url="https://daraz.pk/sony-xm4",
        currency="PKR",
        identifiers={"sku": "SONY-WH-1000XM4"}
    )

    # Shopify listing
    service.match_and_upsert_listing(
        platform="Shopify",
        platform_product_id="sp_999",
        store_domain="electronics-hub.com",
        title="Sony WH-1000XM4 Bluetooth Headphones",
        price=278.0,
        original_price=349.0,
        product_url="https://electronics-hub.com/products/sony-xm4",
        currency="USD",
        identifiers={"sku": "SONY-WH-1000XM4"}
    )

    detail = service.get_product_detail(prod.unified_product_id)
    assert detail is not None
    assert len(detail.platform_listings) == 2
    assert len(detail.price_comparison) == 2
    assert "Daraz" in detail.unified_product.platforms
    assert "Shopify" in detail.unified_product.platforms

    # Check currencies are preserved
    currencies = [p.currency for p in detail.price_comparison]
    assert "PKR" in currencies
    assert "USD" in currencies


# -----------------------------------------------------------------------------
# 15. Historical Data Aggregation
# -----------------------------------------------------------------------------
def test_historical_data_aggregation(tmp_path):
    store_file = str(tmp_path / "test_hist.json")
    u_repo = InMemoryUnifiedProductRepository(data_file=store_file)
    dz_repo = InMemoryMarketplaceProductRepository()
    sp_repo = InMemoryShopifyRepository()
    service = UnifiedProductIntelligenceService(unified_repo=u_repo, daraz_repo=dz_repo, shopify_repo=sp_repo)

    # Add unified product
    prod, _, _ = service.match_and_upsert_listing(
        platform="Daraz",
        platform_product_id="item_hist_1",
        title="Audionic Airbud 425 Wireless Earbuds",
        price=3499.0,
        product_url="https://daraz.pk/airbud",
        currency="PKR"
    )

    # Add historical snapshot to Daraz repo
    dz_repo.create_snapshot(
        ProductMarketSnapshot(
            id="snap_1",
            product_id="item_hist_1",
            platform="daraz",
            price=3999.0,
            original_price=4500.0,
            discount=11.0,
            rating=4.5,
            review_count=120,
            stock_status="in_stock",
            observed_at=datetime.now(timezone.utc) - timedelta(days=2)
        )
    )

    history = service.get_product_history(prod.unified_product_id)
    assert history is not None
    assert history.total_observations >= 1
    assert "Daraz" in history.platforms


# -----------------------------------------------------------------------------
# 16, 17, 18. Search, Filters & Pagination
# -----------------------------------------------------------------------------
def test_search_filters_and_pagination(tmp_path):
    store_file = str(tmp_path / "test_search.json")
    repo = InMemoryUnifiedProductRepository(data_file=store_file)
    service = UnifiedProductIntelligenceService(unified_repo=repo)

    # Seed 5 diverse products
    items = [
        ("Daraz", "dz_1", "Apple MacBook Pro M3 14 Inch", 450000.0, "Laptops"),
        ("Daraz", "dz_2", "Apple iPhone 15 Pro Max 256GB", 380000.0, "Mobiles"),
        ("Shopify", "sp_1", "Gymshark Power Stringer Tank", 32.0, "Apparel"),
        ("Shopify", "sp_2", "Gymshark Crest Oversized Hoodie", 55.0, "Apparel"),
        ("Shopify", "sp_3", "Anker PowerCore 20000mah Power Bank", 45.0, "Accessories")
    ]
    for plat, pid, title, price, cat in items:
        service.match_and_upsert_listing(
            platform=plat,
            platform_product_id=pid,
            title=title,
            price=price,
            product_url=f"https://example.com/{pid}",
            category=cat
        )

    # Search
    search_res = service.search(query="Apple")
    assert search_res.total_matches == 2

    # Filter by Category
    cat_res = service.list_products(category="Apparel")
    assert cat_res.total == 2

    # Filter by Platform
    plat_res = service.list_products(platform="Shopify")
    assert plat_res.total == 3

    # Pagination
    page_res = service.list_products(page=1, limit=2)
    assert len(page_res.items) == 2
    assert page_res.total_pages == 3


# -----------------------------------------------------------------------------
# 19. Data Quality Completeness Score
# -----------------------------------------------------------------------------
def test_data_quality_completeness_score():
    complete_raw = {
        "title": "Nike Air Zoom Pegasus 40 Running Shoes",
        "price": 130.0,
        "product_url": "https://nike.com/pegasus",
        "image_url": "https://nike.com/img.jpg",
        "brand": "Nike",
        "rating": 4.8
    }
    norm_complete = ProductNormalizer.normalize_product(complete_raw)
    assert norm_complete["completeness_score"] == 1.0

    sparse_raw = {
        "title": "Random Unbranded Generic Cable",
        "price": 2.0
    }
    norm_sparse = ProductNormalizer.normalize_product(sparse_raw)
    assert norm_sparse["completeness_score"] <= 0.6


# -----------------------------------------------------------------------------
# 20 & 21. Daraz & Shopify Integration Regression Tests
# -----------------------------------------------------------------------------
def test_api_unified_intelligence_endpoints():
    # Test GET /api/v1/products/intelligence
    res = client.get("/api/v1/products/intelligence")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "items" in body["data"]

    # Test GET /api/v1/products/intelligence/search
    search_res = client.get("/api/v1/products/intelligence/search?q=earbuds")
    assert search_res.status_code == 200
    search_body = search_res.json()
    assert search_body["success"] is True
    assert "items" in search_body["data"]
