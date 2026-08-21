from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.app.models.domain import Alert
from backend.app.services.alert_service import AlertService
from backend.app.api.deps import get_alert_service
from backend.app.schemas.common import ResponseModel

router = APIRouter()

@router.get("", response_model=ResponseModel[List[Alert]])
def list_alerts(
    severity: Optional[str] = "all",
    unread_only: bool = False,
    alert_service: AlertService = Depends(get_alert_service)
):
    items = alert_service.list_alerts(severity=severity, unread_only=unread_only)
    return ResponseModel(
        success=True,
        message="Alerts retrieved successfully",
        data=items
    )

@router.post("/{alert_id}/read", response_model=ResponseModel[Alert])
def mark_alert_read(
    alert_id: str,
    alert_service: AlertService = Depends(get_alert_service)
):
    a = alert_service.mark_read(alert_id)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    return ResponseModel(
        success=True,
        message="Alert marked as read",
        data=a
    )

@router.post("/{alert_id}/resolve", response_model=ResponseModel[Alert])
def resolve_alert(
    alert_id: str,
    alert_service: AlertService = Depends(get_alert_service)
):
    a = alert_service.resolve(alert_id)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    return ResponseModel(
        success=True,
        message="Alert resolved successfully",
        data=a
    )
