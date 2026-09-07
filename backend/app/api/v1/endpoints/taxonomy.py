from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status

from backend.app.api.deps import get_taxonomy_repository
from backend.app.repositories.base import TaxonomyRepository
from backend.app.schemas.taxonomy import (
    TaxonomyCategoryItem,
    TaxonomyTreeNode,
    TaxonomyTreeResponse,
    TaxonomyCategoriesListResponse,
    TaxonomySearchResult,
    TaxonomySearchResponse
)

router = APIRouter()

def _to_tree_node(cat) -> TaxonomyTreeNode:
    children_nodes = [_to_tree_node(c) for c in (getattr(cat, "children", []) or [])]
    return TaxonomyTreeNode(
        id=cat.id,
        parent_id=cat.parent_id,
        name=cat.name,
        slug=cat.slug,
        level=cat.level,
        description=cat.description or "",
        is_active=cat.is_active,
        product_count=getattr(cat, "product_count", 0) or 0,
        children=children_nodes
    )

@router.get(
    "/categories",
    response_model=TaxonomyCategoriesListResponse,
    summary="List flat categories in TrendPulse taxonomy"
)
def list_categories(
    parent_id: Optional[str] = Query(None, description="Filter by parent category ID"),
    level: Optional[int] = Query(None, description="Filter by hierarchy level (1=Category, 2=Subcategory, 4=Product Type)"),
    repo: TaxonomyRepository = Depends(get_taxonomy_repository)
):
    cats = repo.list_categories(parent_id=parent_id, level=level)
    counts = repo.get_category_product_counts()
    items = [
        TaxonomyCategoryItem(
            id=c.id,
            parent_id=c.parent_id,
            name=c.name,
            slug=c.slug,
            level=c.level,
            description=c.description or "",
            is_active=c.is_active,
            product_count=counts.get(c.name, 0),
            created_at=c.created_at,
            updated_at=c.updated_at
        )
        for c in cats
    ]
    return TaxonomyCategoriesListResponse(
        total=len(items),
        items=items
    )

@router.get(
    "/tree",
    response_model=TaxonomyTreeResponse,
    summary="Get hierarchical taxonomy tree with database product counts"
)
def get_taxonomy_tree(
    repo: TaxonomyRepository = Depends(get_taxonomy_repository)
):
    tree_roots = repo.get_taxonomy_tree()
    nodes = [_to_tree_node(r) for r in tree_roots]
    return TaxonomyTreeResponse(
        total_nodes=len(nodes),
        categories=nodes
    )

@router.get(
    "/search",
    response_model=TaxonomySearchResponse,
    summary="Search categories in TrendPulse taxonomy"
)
def search_taxonomy(
    q: str = Query(..., min_length=1, description="Search term for taxonomy category or product type"),
    limit: int = Query(20, ge=1, le=100),
    repo: TaxonomyRepository = Depends(get_taxonomy_repository)
):
    results_raw = repo.search_categories(query=q, limit=limit)
    items = [
        TaxonomySearchResult(
            id=r["id"],
            name=r["name"],
            slug=r["slug"],
            level=r["level"],
            path=r.get("path", [r["name"]]),
            product_count=r.get("product_count", 0)
        )
        for r in results_raw
    ]
    return TaxonomySearchResponse(
        query=q,
        total=len(items),
        results=items
    )

@router.get(
    "/counts",
    response_model=Dict[str, int],
    summary="Get product counts per category in real database"
)
def get_category_counts(
    repo: TaxonomyRepository = Depends(get_taxonomy_repository)
):
    return repo.get_category_product_counts()
