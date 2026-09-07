"""Configuration settings and tuning parameters for the Product Extraction Engine."""

from typing import Dict, List
from pydantic import BaseModel, Field


class DarazExtractionConfig(BaseModel):
    """Tuning and behavior configuration for Daraz product extraction."""

    # Concurrency and Performance
    max_concurrency: int = Field(default=8, description="Maximum concurrent product extraction workers")
    batch_size: int = Field(default=50, description="Number of products to persist in a single batch")
    request_timeout_seconds: float = Field(default=15.0, description="HTTP request timeout")
    browser_timeout_seconds: float = Field(default=30.0, description="Playwright navigation timeout")

    # Extraction Strategies
    enable_http_first: bool = Field(default=True, description="Attempt fast async HTTP before browser fallback")
    auto_browser_fallback: bool = Field(default=True, description="Fallback to Playwright if page is CSR/incomplete")
    scroll_pages_for_lazy_loading: bool = Field(default=True, description="Scroll product page to trigger lazy content")
    scroll_steps: int = Field(default=3, description="Number of scroll steps in browser fallback")
    scroll_delay_ms: int = Field(default=300, description="Delay between scroll steps in ms")

    # Image Extraction Preferences
    prefer_high_res_images: bool = Field(default=True, description="Strip thumbnail resizing tokens from image URLs")
    max_gallery_images: int = Field(default=20, description="Maximum gallery image URLs to store per product")

    # Confidence Thresholds
    min_overall_confidence: float = Field(default=0.60, description="Minimum weighted confidence score for valid status")
    field_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "title": 0.25,
            "price": 0.25,
            "images": 0.15,
            "seller": 0.10,
            "category": 0.10,
            "rating": 0.05,
            "description": 0.05,
            "specifications": 0.05,
        },
        description="Weights for overall product confidence scoring",
    )

    # Validation Rules
    required_fields: List[str] = Field(
        default_factory=lambda: ["product_id", "title", "price", "url"],
        description="Fields strictly required for a product to be VALID",
    )


default_extraction_config = DarazExtractionConfig()
