from typing import List
from backend.app.models.domain import Product
from backend.app.repositories.base import WatchlistRepository, ProductRepository

class WatchlistService:
    """
    Manages watchlist business rules, duplicate prevention,
    and product watchlisted state synchronization.
    """

    def __init__(self, watchlist_repo: WatchlistRepository, product_repo: ProductRepository):
        self.watchlist = watchlist_repo
        self.products = product_repo

    def get_watchlist(self, user_id: str) -> List[Product]:
        ids = self.watchlist.list_product_ids(user_id)
        all_prods = {p.id: p for p in self.products.list()}
        items: List[Product] = []
        for pid in ids:
            if pid in all_prods:
                p = all_prods[pid]
                p.is_watchlisted = True
                items.append(p)
        return items

    def add_to_watchlist(self, user_id: str, product_id: str) -> bool:
        # Check product exists
        product = self.products.get_by_id(product_id)
        if not product:
            return False
        
        # Add to repository (thread-safe, idempotent)
        success = self.watchlist.add(user_id, product_id)
        if success:
            product.is_watchlisted = True
            self.products.update(product)
        return success

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
