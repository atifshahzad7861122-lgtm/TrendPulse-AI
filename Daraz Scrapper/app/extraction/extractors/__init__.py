"""Domain-specific extractors for individual product attributes."""

from app.extraction.extractors.availability import AvailabilityExtractor
from app.extraction.extractors.category import CategoryExtractor
from app.extraction.extractors.description import DescriptionExtractor
from app.extraction.extractors.image import ImageExtractor
from app.extraction.extractors.price import PriceExtractor
from app.extraction.extractors.rating import RatingExtractor
from app.extraction.extractors.sales import SalesExtractor
from app.extraction.extractors.seller import SellerExtractor
from app.extraction.extractors.specification import SpecificationExtractor
from app.extraction.extractors.title import TitleExtractor
from app.extraction.extractors.variant import VariantExtractor

__all__ = [
    "AvailabilityExtractor",
    "CategoryExtractor",
    "DescriptionExtractor",
    "ImageExtractor",
    "PriceExtractor",
    "RatingExtractor",
    "SalesExtractor",
    "SellerExtractor",
    "SpecificationExtractor",
    "TitleExtractor",
    "VariantExtractor",
]
