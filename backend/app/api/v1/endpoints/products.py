from typing import List, Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.app.models.domain import Product, User, MarketplaceProduct, ProductMarketSnapshot
from backend.app.services.intelligence import ProductIntelligenceEngine
from backend.app.services.watchlist_service import WatchlistService
from backend.app.services.daraz_service import DarazService
from backend.app.repositories.base import MarketplaceProductRepository
from backend.app.schemas.daraz import DarazProductItem
from backend.app.api.deps import (
    get_product_intelligence_engine, get_watchlist_service, get_current_user, get_daraz_service, get_marketplace_product_repository
)
from backend.app.schemas.common import ResponseModel

logger = logging.getLogger(__name__)
router = APIRouter()

def _daraz_item_to_product(dp: DarazProductItem) -> Product:
    if dp.rating and dp.rating > 0:
        score = round(min(99.0, max(50.0, dp.rating * 16.0 + min(dp.sold_count or 0, 100) * 0.1)), 1)
        sentiment = round(dp.rating / 5.0, 2)
    else:
        score = 0.0
        sentiment = 0.0

    return Product(
        id=f"daraz_{dp.product_id}",
        name=dp.name,
        category=dp.category or "Marketplace",
        sub_category=dp.brand or "Daraz PK",
        trend_score=score,
        growth_rate=0.0,
        volume=dp.sold_count or dp.review_count or 0,
        velocity_label="Breakout" if score >= 85 else ("Surging" if score >= 75 else ("Steady" if score > 0 else "Insufficient Data")),
        status="Active",
        price_range=f"PKR {dp.price:,.0f}" if dp.price > 0 else "Price on Request",
        primary_platform="Daraz",
        platforms=["Daraz"],
        platform_shares={"Daraz": 1.0},
        historical_scores=[],
        historical_prices=[],
        ai_summary=f"Daraz Pakistan verified product with {dp.rating or 0}★ rating ({dp.review_count or 0} reviews) from seller '{dp.seller_name or 'Daraz Verified'}'.",
        signals_count=dp.review_count or 0,
        sentiment_score=sentiment,
        image_url=dp.image_url,
        tags=[t for t in [dp.brand, dp.location, "Daraz PK", "Verified"] if t],
        is_watchlisted=False,
        provenance="live_ingested_signals",
        observation_count=1,
        historical_observation_count=0,
        data_sufficiency="live_data" if dp.price > 0 else "insufficient_data",
        raw_data={
            "daraz_product": dp.model_dump(),
            "source": "daraz.pk",
            "product_url": dp.product_url,
            "location": dp.location,
            "brand": dp.brand,
            "original_price": dp.original_price,
            "discount_label": dp.discount_label,
            "sku": dp.sku,
            "seller_name": dp.seller_name,
            "seller_id": dp.seller_id
        }
    )

def _marketplace_product_to_product(mp: MarketplaceProduct, snapshots: Optional[List[ProductMarketSnapshot]] = None) -> Product:
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

@router.get("", response_model=ResponseModel[List[Product]])
def list_products(
    category: Optional[str] = "all",
    platform: Optional[str] = "all",
    search: Optional[str] = None,
    sort_by: Optional[str] = "trend_score",
    page: int = Query(1, ge=1, description="Page number"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Items limit"),
    intelligence: ProductIntelligenceEngine = Depends(get_product_intelligence_engine),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
    daraz_service: DarazService = Depends(get_daraz_service),
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository),
    current_user: User = Depends(get_current_user)
):
    items: List[Product] = []
    seen_ids = set()

    # 1. Base standard products
    base_items = intelligence.list_products(category=category, platform=platform, search=search, sort_by=sort_by)
    for p in base_items:
        if p.id not in seen_ids:
            items.append(p)
            seen_ids.add(p.id)

    # 2. Persisted marketplace products from scraper
    if marketplace_repo:
        try:
            mp_list = marketplace_repo.list_products(limit=500)
            for mp in mp_list:
                clean_pid = mp.id if mp.id.startswith(f"{mp.platform}_") else f"{mp.platform}_{mp.product_id}"
                if clean_pid in seen_ids or mp.id in seen_ids:
                    continue
                
                # Category filter
                if category and category.lower() != "all":
                    mp_cat = (mp.category or "").strip().lower()
                    cat_query = category.strip().lower()
                    if not mp_cat or (cat_query not in mp_cat and mp_cat not in cat_query):
                        continue

                # Platform filter
                if platform and platform.lower() != "all":
                    if platform.lower() != (mp.platform or "").lower():
                        continue

                # Search filter
                if search and search.strip():
                    q = search.strip().lower()
                    if q not in mp.product_name.lower() and (not mp.category or q not in mp.category.lower()) and (not mp.brand or q not in mp.brand.lower()):
                        continue

                snaps = marketplace_repo.get_snapshots(mp.platform, mp.product_id)
                prod = _marketplace_product_to_product(mp, snaps)
                items.append(prod)
                seen_ids.add(clean_pid)
                seen_ids.add(mp.id)
        except Exception as e:
            logger.debug(f"Error loading marketplace products: {e}")

    # 3. If platform is specifically Daraz and no local items match, or search was performed
    if platform and platform.lower() == "daraz" and not items:
        try:
            query_term = search.strip() if search and search.strip() else (category if category and category.lower() != "all" else "trending")
            daraz_resp = daraz_service.search_products(
                query=query_term,
                page=1,
                category=category if category and category.lower() != "all" else None
            )
            live_items = [_daraz_item_to_product(dp) for dp in daraz_resp.products]
            for p in live_items:
                if p.id not in seen_ids:
                    items.append(p)
                    seen_ids.add(p.id)
        except Exception as e:
            logger.warning(f"Failed to fetch live Daraz products in list_products: {e}")
    elif search and search.strip() and (platform == "all" or not platform) and len(items) < 3:
        try:
            daraz_resp = daraz_service.search_products(query=search.strip(), page=1)
            daraz_items = [_daraz_item_to_product(dp) for dp in daraz_resp.products[:6]]
            for p in daraz_items:
                if p.id not in seen_ids:
                    items.append(p)
                    seen_ids.add(p.id)
        except Exception as e:
            logger.warning(f"Failed to augment search with Daraz products: {e}")

    # 4. Sorting
    if sort_by == "growth":
        items.sort(key=lambda x: x.growth_rate, reverse=True)
    elif sort_by == "volume":
        items.sort(key=lambda x: x.volume, reverse=True)
    elif sort_by == "sentiment":
        items.sort(key=lambda x: x.sentiment_score, reverse=True)
    else:
        items.sort(key=lambda x: x.trend_score, reverse=True)

    # 5. Sync is_watchlisted flag
    for p in items:
        p.is_watchlisted = watchlist_service.is_watched(current_user.id, p.id)
    
    # 6. Pagination slicing if limit specified
    if limit is not None:
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        items = items[start_idx:end_idx]

    return ResponseModel(
        success=True,
        message="Products retrieved successfully",
        data=items
    )

@router.get("/compare", response_model=ResponseModel[List[Product]])
def compare_products(
    ids: str = Query(..., description="Comma-separated product IDs e.g. prod_01,prod_02"),
    intelligence: ProductIntelligenceEngine = Depends(get_product_intelligence_engine),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
    daraz_service: DarazService = Depends(get_daraz_service),
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository),
    current_user: User = Depends(get_current_user)
):
    product_ids = [i.strip() for i in ids.split(",") if i.strip()]
    if not product_ids:
        raise HTTPException(status_code=400, detail="Please provide at least one product ID to compare")
    
    results: List[Product] = []
    for pid in product_ids:
        # 1. Check standard product repo via intelligence
        local_results = intelligence.compare_products([pid])
        if local_results:
            results.append(local_results[0])
            continue
        
        # 2. Check MarketplaceProductRepository (e.g. persisted Daraz scrape)
        raw_id = pid.replace("daraz_", "").replace("mp_item_", "")
        mp = marketplace_repo.get_product("daraz", raw_id)
        if not mp:
            all_mp = marketplace_repo.list_products(limit=200)
            mp = next((p for p in all_mp if p.id == pid or p.product_id == raw_id or p.product_id == pid), None)
            
        if mp:
            snapshots = marketplace_repo.get_snapshots(platform=mp.platform, product_id=mp.product_id)
            p = _marketplace_product_to_product(mp, snapshots)
            results.append(p)
            continue
            
        # 3. If pid starts with daraz_, attempt live details via daraz_service
        if pid.startswith("daraz_"):
            try:
                details = daraz_service.get_product_details(item_id=raw_id)
                dp_item = DarazProductItem(
                    product_id=details.product_id,
                    name=details.name,
                    price=details.price,
                    original_price=details.original_price,
                    discount=details.discount,
                    currency=details.currency,
                    rating=details.rating,
                    review_count=details.review_count,
                    seller_name=details.seller.name if details.seller else None,
                    seller_id=details.seller.seller_id if details.seller else None,
                    brand=details.brand,
                    category=details.category,
                    image_url=details.main_image or (details.images[0] if details.images else None),
                    product_url=details.product_url,
                    in_stock=details.in_stock,
                    location="Pakistan",
                    source="daraz.pk"
                )
                p = _daraz_item_to_product(dp_item)
                results.append(p)
            except Exception as e:
                logger.warning(f"Error fetching Daraz product for comparison: {e}")

    for p in results:
        p.is_watchlisted = watchlist_service.is_watched(current_user.id, p.id)
            
    return ResponseModel(
        success=True,
        message="Product comparison data retrieved",
        data=results
    )

@router.get("/{product_id}", response_model=ResponseModel[Product])
def get_product_detail(
    product_id: str,
    intelligence: ProductIntelligenceEngine = Depends(get_product_intelligence_engine),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
    daraz_service: DarazService = Depends(get_daraz_service),
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository),
    current_user: User = Depends(get_current_user)
):
    # 1. Check local standard intelligence products
    p = intelligence.get_product_intelligence(product_id)
    if p:
        p.is_watchlisted = watchlist_service.is_watched(current_user.id, p.id)
        return ResponseModel(
            success=True,
            message="Product detail retrieved",
            data=p
        )

    # 2. Check MarketplaceProductRepository
    raw_id = product_id.replace("daraz_", "").replace("mp_item_", "")
    mp = marketplace_repo.get_product("daraz", raw_id)
    if not mp:
        all_mp = marketplace_repo.list_products(limit=200)
        mp = next((m for m in all_mp if m.id == product_id or m.product_id == raw_id or m.product_id == product_id), None)

    if mp:
        snapshots = marketplace_repo.get_snapshots(platform=mp.platform, product_id=mp.product_id)
        prod = _marketplace_product_to_product(mp, snapshots)
        prod.is_watchlisted = watchlist_service.is_watched(current_user.id, prod.id)
        return ResponseModel(
            success=True,
            message="Marketplace product intelligence retrieved",
            data=prod
        )

    # 3. If starts with daraz_, attempt live details
    if product_id.startswith("daraz_"):
        try:
            details = daraz_service.get_product_details(item_id=raw_id)
            dp_item = DarazProductItem(
                product_id=details.product_id,
                name=details.name,
                price=details.price,
                original_price=details.original_price,
                discount=details.discount,
                discount_label=details.discount_label,
                currency=details.currency,
                rating=details.rating,
                review_count=details.review_count,
                seller_name=details.seller.name if details.seller else None,
                seller_id=details.seller.seller_id if details.seller else None,
                brand=details.brand,
                category=details.category,
                image_url=details.main_image or (details.images[0] if details.images else None),
                product_url=details.product_url,
                in_stock=details.in_stock,
                location="Pakistan",
                source="daraz.pk"
            )
            p = _daraz_item_to_product(dp_item)
            p.raw_data["daraz_details"] = details.model_dump()
            p.is_watchlisted = watchlist_service.is_watched(current_user.id, p.id)
            return ResponseModel(
                success=True,
                message="Daraz product intelligence retrieved",
                data=p
            )
        except Exception as e:
            logger.error(f"Error fetching Daraz product details for {product_id}: {e}")
            raise HTTPException(status_code=404, detail=f"Daraz product not found: {str(e)}")

    raise HTTPException(status_code=404, detail="Product not found")

