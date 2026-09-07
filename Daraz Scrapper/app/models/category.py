"""Category hierarchy data model."""

from typing import Optional
from pydantic import BaseModel, Field


class Category(BaseModel):
    """Category classification schema."""
    category_id: str = Field(..., description="Unique category identifier or slug")
    parent_id: Optional[str] = Field(default=None, description="Parent category ID for tree traversal")
    name: str = Field(..., description="Category display name")
    url: Optional[str] = Field(default=None, description="Category listing page URL")
    level: int = Field(default=1, ge=1, description="Category depth level in the hierarchy")
    is_leaf: bool = Field(default=False, description="True if category has no further subcategories")
