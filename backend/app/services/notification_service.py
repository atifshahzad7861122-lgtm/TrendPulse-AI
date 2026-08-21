from typing import List, Optional
from datetime import datetime, timezone
import uuid
from backend.app.models.domain import Notification
from backend.app.repositories.base import NotificationRepository

class NotificationService:
    """
    Handles event-driven notification dispatch and user read state.
    """

    def __init__(self, notification_repo: NotificationRepository):
        self.notifications = notification_repo

    def list_notifications(self, unread_only: bool = False) -> List[Notification]:
        return self.notifications.list(unread_only=unread_only)

    def mark_read(self, notification_id: str) -> Optional[Notification]:
        return self.notifications.mark_read(notification_id)

    def mark_all_read(self) -> int:
        return self.notifications.mark_all_read()

    def dispatch(
        self,
        title: str,
        message: str,
        type_: str = "system",
        link: Optional[str] = None
    ) -> Notification:
        n = Notification(
            id=f"notif_{uuid.uuid4().hex[:8]}",
            title=title,
            message=message,
            type=type_,
            is_read=False,
            link=link,
            created_at=datetime.now(timezone.utc)
        )
        # Note: in-memory repo can store it if extended or prepend
        return n
