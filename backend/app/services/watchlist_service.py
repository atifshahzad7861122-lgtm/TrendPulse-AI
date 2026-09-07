from typing import List, Optional, Any
from backend.app.models.domain import Product, MarketplaceProduct
from backend.app.repositories.base import (
    WatchlistRepository, ProductRepository, MarketplaceProductRepository, UnifiedProductRepository
)

def _mp_to_product(mp: MarketplaceProduct, snapshots: Optional[List[Any]] = None) -> Product:
    snaps = sorted(snapshots or [], key=lambda s: getattr(s, "observed_at", None) or 0)
    hist_prices = [{"date": s.observed_at.strftime("%b %d"), "price": s.price} for s in snaps if getattr(s, "price", 0) > 0 and hasattr(s, "observed_at")]
    
    growth_rate = 0.0
    if len(hist_prices) >= 2 and hist_prices[0]["price"] > 0:
        growth_rate = round(((hist_prices[-1]["price"] - hist_prices[0]["price"]) / hist_prices[0]["price"]) * 100, 1)

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
        historical_scores=[],
        historical_prices=hist_prices,
        ai_summary=f"{platform_title} verified product with {mp.rating or 0}★ rating ({mp.review_count or 0} reviews).",
        signals_count=mp.review_count or 0,
        sentiment_score=sentiment,
        image_url=mp.image_url,
        tags=[t for t in [brand_name, mp.location, f"{platform_title} PK", "Verified"] if t],
        is_watchlisted=True,
        provenance="persisted_marketplace_observations",
        observation_count=1 + len(snaps),
        historical_observation_count=len(snaps),
        data_sufficiency="live_data" if mp.price > 0 else "insufficient_data"
    )

class WatchlistService:
    """
    Manages watchlist business rules, duplicate prevention,
    and product watchlisted state synchronization across all product repositories.
    """

    def __init__(
        self,
        watchlist_repo: WatchlistRepository,
        product_repo: ProductRepository,
        marketplace_repo: Optional[MarketplaceProductRepository] = None,
        unified_repo: Optional[UnifiedProductRepository] = None
    ):
        self.watchlist = watchlist_repo
        self.products = product_repo
        self.marketplace_repo = marketplace_repo
        self.unified_repo = unified_repo

    def get_watchlist(self, user_id: str) -> List[Product]:
        ids = self.watchlist.list_product_ids(user_id)
        if not ids:
            return []

        all_prods: dict[str, Product] = {}
        for p in self.products.list():
            all_prods[p.id] = p

        if self.marketplace_repo:
            try:
                for mp in self.marketplace_repo.list_products(limit=1000):
                    clean_id = mp.id if mp.id.startswith(f"{mp.platform}_") else f"{mp.platform}_{mp.product_id}"
                    if clean_id not in all_prods and mp.id not in all_prods:
                        snaps = self.marketplace_repo.get_snapshots(mp.platform, mp.product_id)
                        prod = _mp_to_product(mp, snaps)
                        all_prods[clean_id] = prod
                        all_prods[mp.id] = prod
                        all_prods[mp.product_id] = prod
            except Exception:
                pass

        items: List[Product] = []
        for pid in ids:
            if pid in all_prods:
                p = all_prods[pid]
                p.is_watchlisted = True
                if p not in items:
                    items.append(p)
            elif self.marketplace_repo:
                raw_id = pid.replace("daraz_", "").replace("mp_item_", "")
                mp = self.marketplace_repo.get_product("daraz", raw_id)
                if mp:
                    snaps = self.marketplace_repo.get_snapshots(mp.platform, mp.product_id)
                    p = _mp_to_product(mp, snaps)
                    p.is_watchlisted = True
                    if p not in items:
                        items.append(p)

        return items

    def add_to_watchlist(self, user_id: str, product_id: str) -> bool:
        # Check standard product repo
        product = self.products.get_by_id(product_id)
        if product:
            success = self.watchlist.add(user_id, product_id)
            if success:
                product.is_watchlisted = True
                self.products.update(product)
            return success
        
        # Check marketplace product repo
        if self.marketplace_repo:
            raw_id = product_id.replace("daraz_", "").replace("mp_item_", "")
            mp = self.marketplace_repo.get_product("daraz", raw_id)
            if not mp:
                all_mps = self.marketplace_repo.list_products(limit=200)
                mp = next((m for m in all_mps if m.id == product_id or m.product_id == raw_id or m.product_id == product_id), None)
            if mp:
                return self.watchlist.add(user_id, product_id)

        # Allow adding if ID is a valid formatted product ID
        if product_id.startswith("daraz_") or product_id.startswith("prod_") or product_id.startswith("mp_"):
            return self.watchlist.add(user_id, product_id)

        return False

    def remove_from_watchlist(self, user_id: str, product_id: str) -> bool:
        success = self.watchlist.remove(user_id, product_id)
        if success:
            product = self.products.get_by_id(product_id)
            if product:
                product.is_watchlisted = False
                self.products.update(product)
        return success

    def is_watched(self, user_id: str, product_id: str) -> bool:
        return self.watchlist.is_in_watchlist(user_id, product_id)

