from typing import List, Optional
from backend.app.models.domain import Category
from backend.app.repositories.base import CategoryRepository, ProductRepository
from backend.app.domain.aggregation import AggregationEngine

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
    from underlying product intelligence metrics.
    """

    def __init__(self, category_repo: CategoryRepository, product_repo: ProductRepository):
        self.categories = category_repo
        self.products = product_repo

    def list_categories(self) -> List[Category]:
        all_products = self.products.list()
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
