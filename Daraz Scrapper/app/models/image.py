"""Image data model."""

from typing import Optional
import uuid
from pydantic import BaseModel, Field, HttpUrl


class Image(BaseModel):
    """Product image schema."""
    image_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: Optional[str] = Field(default=None, description="Associated product ID")
    url: str = Field(..., description="Image URL")
    position: int = Field(default=0, ge=0, description="Image ordering index")
    is_primary: bool = Field(default=False, description="Whether this is the main product thumbnail")
