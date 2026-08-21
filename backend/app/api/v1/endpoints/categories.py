from typing import List
from fastapi import APIRouter, Depends, HTTPException
from backend.app.models.domain import Category
from backend.app.services.category_service import CategoryService
from backend.app.api.deps import get_category_service
from backend.app.schemas.common import ResponseModel

router = APIRouter()

@router.get("", response_model=ResponseModel[List[Category]])
def list_categories(category_service: CategoryService = Depends(get_category_service)):
    items = category_service.list_categories()
    return ResponseModel(
        success=True,
        message="Categories retrieved successfully",
        data=items
    )

@router.get("/{category_id}", response_model=ResponseModel[Category])
def get_category(category_id: str, category_service: CategoryService = Depends(get_category_service)):
    c = category_service.get_category_by_id(category_id)
    if not c:
        raise HTTPException(status_code=404, detail="Category not found")
    return ResponseModel(
        success=True,
        message="Category retrieved successfully",
        data=c
    )
