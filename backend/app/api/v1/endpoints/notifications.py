from typing import List
from fastapi import APIRouter, Depends, HTTPException
from backend.app.models.domain import Notification
from backend.app.services.notification_service import NotificationService
from backend.app.api.deps import get_notification_service
from backend.app.schemas.common import ResponseModel

router = APIRouter()

@router.get("", response_model=ResponseModel[List[Notification]])
def list_notifications(
    unread_only: bool = False,
    notification_service: NotificationService = Depends(get_notification_service)
):
    items = notification_service.list_notifications(unread_only=unread_only)
    return ResponseModel(
        success=True,
        message="Notifications retrieved successfully",
        data=items
    )

@router.post("/{notification_id}/read", response_model=ResponseModel[Notification])
def mark_notification_read(
    notification_id: str,
    notification_service: NotificationService = Depends(get_notification_service)
):
    n = notification_service.mark_read(notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    return ResponseModel(
        success=True,
        message="Notification marked as read",
        data=n
    )

@router.post("/read-all", response_model=ResponseModel[dict])
def mark_all_notifications_read(
    notification_service: NotificationService = Depends(get_notification_service)
):
    count = notification_service.mark_all_read()
    return ResponseModel(
        success=True,
        message=f"{count} notifications marked as read",
        data={"count": count}
    )
