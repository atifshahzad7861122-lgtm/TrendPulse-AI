from typing import List
from fastapi import APIRouter, Depends, HTTPException
from backend.app.models.domain import PlatformMetrics
from backend.app.services.platform_service import PlatformService
from backend.app.api.deps import get_platform_service
from backend.app.schemas.common import ResponseModel

router = APIRouter()

@router.get("", response_model=ResponseModel[List[PlatformMetrics]])
def list_platforms(platform_service: PlatformService = Depends(get_platform_service)):
    items = platform_service.list_platforms()
    return ResponseModel(
        success=True,
        message="Platforms retrieved successfully",
        data=items
    )

@router.get("/{slug}", response_model=ResponseModel[PlatformMetrics])
def get_platform(slug: str, platform_service: PlatformService = Depends(get_platform_service)):
    p = platform_service.get_platform_by_slug(slug)
    if not p:
        raise HTTPException(status_code=404, detail="Platform not found")
    return ResponseModel(
        success=True,
        message="Platform retrieved successfully",
        data=p
    )
