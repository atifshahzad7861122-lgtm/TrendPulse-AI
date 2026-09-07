"""Marketplace adapter package exports."""

from app.crawling.marketplaces.base import BaseMarketplaceAdapter
from app.crawling.marketplaces.daraz import DarazAdapter
from app.crawling.marketplaces.amazon import AmazonAdapter
from app.crawling.marketplaces.ebay import EbayAdapter
from app.crawling.marketplaces.aliexpress import AliExpressAdapter
from app.crawling.marketplaces.shopify import ShopifyAdapter

__all__ = [
    "BaseMarketplaceAdapter",
    "DarazAdapter",
    "AmazonAdapter",
    "EbayAdapter",
    "AliExpressAdapter",
    "ShopifyAdapter",
]
