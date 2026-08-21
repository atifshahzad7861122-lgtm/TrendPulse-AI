from fastapi import APIRouter, Depends, Query
from backend.app.services.search_service import SearchService
from backend.app.api.deps import get_search_service
from backend.app.schemas.entities import SearchResponse
from backend.app.schemas.common import ResponseModel

router = APIRouter()

@router.get("", response_model=ResponseModel[SearchResponse])
def global_search(
    q: str = Query(..., min_length=1),
    search_service: SearchService = Depends(get_search_service)
):
    search_result = search_service.search(q)
    return ResponseModel(
        success=True,
        message=f"Found {search_result.total_results} matches for '{q}'",
        data=search_result
    )
