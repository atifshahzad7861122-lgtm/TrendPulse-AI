from typing import List, Optional
from backend.app.models.domain import Category, Product
from backend.app.repositories.base import CategoryRepository, ProductRepository, MarketplaceProductRepository
from backend.app.domain.aggregation import AggregationEngine
from backend.app.domain.classification import CategoryClassificationService

CATEGORY_DEFINITIONS = [
    ("Beauty & Personal Care", "beauty-personal-care", "Skincare, color cosmetics, hair wellness, and clean beauty formulas."),
    ("Sports & Outdoor", "sports-outdoor", "Running apparel, hydration packs, recovery tech, and outdoor gear."),
    ("Consumer Electronics", "consumer-electronics", "Smart wearables, mobile MagSafe accessories, and desktop audio."),
    ("Home & Living", "home-living", "Ceremonial beverage prep, ergonomic home goods, and kitchenware."),
    ("Fashion & Apparel", "fashion-apparel", "Functional streetwear, activewear sets, and viral accessories."),
]

class CategoryService:
    """
    Dynamically computes category-level analytics derived directly
    from underlying product intelligence metrics and persisted marketplace observations.
    """

    def __init__(
        self,
        category_repo: CategoryRepository,
        product_repo: ProductRepository,
        marketplace_repo: Optional[MarketplaceProductRepository] = None
    ):
        self.categories = category_repo
        self.products = product_repo
        self.marketplace_repo = marketplace_repo

    def list_categories(self) -> List[Category]:
        all_products: List[Product] = list(self.products.list())
        existing_names = {p.name.lower() for p in all_products}

        # Include real persisted marketplace products
        if self.marketplace_repo:
            try:
                mp_products = self.marketplace_repo.list_products()
                for mp in mp_products:
                    if mp.product_name.lower() in existing_names:
                        continue
                    
                    cat_name = mp.category or ""
                    if not cat_name or cat_name.lower() in ("unclassified", "general"):
                        classified = CategoryClassificationService.classify(mp.product_name)
                        cat_name = classified.category

                    # Normalize category name
                    if "beauty" in cat_name.lower() or "skincare" in cat_name.lower() or "cosmetic" in cat_name.lower():
                        cat_name = "Beauty & Personal Care"
                    elif "sport" in cat_name.lower() or "outdoor" in cat_name.lower() or "fitness" in cat_name.lower():
                        cat_name = "Sports & Outdoor"
                    elif "electronic" in cat_name.lower() or "gadget" in cat_name.lower() or "audio" in cat_name.lower() or "phone" in cat_name.lower():
                        cat_name = "Consumer Electronics"
                    elif "home" in cat_name.lower() or "kitchen" in cat_name.lower() or "living" in cat_name.lower():
                        cat_name = "Home & Living"
                    elif "fashion" in cat_name.lower() or "apparel" in cat_name.lower() or "clothing" in cat_name.lower():
                        cat_name = "Fashion & Apparel"

                    platform_title = (mp.platform or "daraz").title()
                    all_products.append(
                        Product(
                            id=f"mp_item_{mp.product_id}",
                            name=mp.product_name,
                            category=cat_name,
                            trend_score=0.0,
                            growth_rate=0.0,
                            volume=max(mp.review_count * 10, 100),
                            price_range=f"{mp.currency} {mp.price:.0f}",
                            primary_platform=platform_title,
                            platforms=[platform_title]
                        )
                    )
            except Exception:
                pass

        aggregated: List[Category] = []
        for name, slug, desc in CATEGORY_DEFINITIONS:
            cat = AggregationEngine.aggregate_category_metrics(
                category_name=name,
                category_slug=slug,
                category_desc=desc,
                products=all_products
            )
            aggregated.append(cat)
        return aggregated

    def get_category_by_id(self, category_id: str) -> Optional[Category]:
        cats = self.list_categories()
        for c in cats:
            if c.id == category_id or c.slug == category_id:
                return c
        return None
