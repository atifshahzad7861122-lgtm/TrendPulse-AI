from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from backend.app.models.domain import User
from backend.app.api.deps import get_dashboard_service, get_current_user
from backend.app.services.dashboard_service import DashboardService
from backend.app.schemas.entities import DashboardSummaryResponse, TrendPoint
from backend.app.schemas.common import ResponseModel

router = APIRouter()

@router.get("/summary", response_model=ResponseModel[DashboardSummaryResponse])
def get_dashboard_summary(
    time_range: str = Query("30d", enum=["7d", "30d", "all"]),
    category: Optional[str] = "all",
    platform: Optional[str] = "all",
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    current_user: User = Depends(get_current_user)
):
    summary_data = dashboard_service.get_summary(
        time_range=time_range,
        category=category,
        platform=platform
    )
    return ResponseModel(
        success=True,
        message="Dashboard summary retrieved",
        data=summary_data
    )

@router.get("/trends", response_model=ResponseModel[List[TrendPoint]])
def get_dashboard_trends(
    time_range: str = Query("30d", enum=["7d", "30d", "all"]),
    category: Optional[str] = "all",
    platform: Optional[str] = "all",
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    points = dashboard_service.get_trends(
        time_range=time_range,
        category=category,
        platform=platform
    )
    return ResponseModel(
        success=True,
        message="Trend time-series points retrieved",
        data=points
    )
