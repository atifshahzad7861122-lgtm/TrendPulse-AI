from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TaxonomyCategoryItem(BaseModel):
    id: str
    parent_id: Optional[str] = None
    name: str
    slug: str
    level: int
    description: str = ""
    is_active: bool = True
    product_count: int = 0
    created_at: datetime
    updated_at: datetime

class TaxonomyTreeNode(BaseModel):
    id: str
    parent_id: Optional[str] = None
    name: str
    slug: str
    level: int
    description: str = ""
    is_active: bool = True
    product_count: int = 0
    children: List["TaxonomyTreeNode"] = Field(default_factory=list)

class TaxonomyTreeResponse(BaseModel):
    total_nodes: int
    categories: List[TaxonomyTreeNode]

class TaxonomyCategoriesListResponse(BaseModel):
    total: int
    items: List[TaxonomyCategoryItem]

class TaxonomySearchResult(BaseModel):
    id: str
    name: str
    slug: str
    level: int
    path: List[str]
    product_count: int = 0

class TaxonomySearchResponse(BaseModel):
    query: str
    total: int
    results: List[TaxonomySearchResult]
