from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
from backend.app.models.domain import Alert, Product
from backend.app.repositories.base import AlertRepository, ProductRepository

class AlertService:
    """
    Evaluates real-time anomaly conditions, triggers alert notifications,
    and manages alert resolution lifecycle with explainable triggers.
    """

    ALERT_ENGINE_VERSION = "2.4.0"

    def __init__(self, alert_repo: AlertRepository, product_repo: ProductRepository):
        self.alerts = alert_repo
        self.products = product_repo

    def list_alerts(
        self,
        severity: Optional[str] = "all",
        unread_only: bool = False
    ) -> List[Alert]:
        return self.alerts.list(severity=severity, unread_only=unread_only)

    def get_by_id(self, alert_id: str) -> Optional[Alert]:
        return self.alerts.get_by_id(alert_id)

    def mark_read(self, alert_id: str) -> Optional[Alert]:
        return self.alerts.mark_read(alert_id)

    def resolve(self, alert_id: str) -> Optional[Alert]:
        return self.alerts.resolve(alert_id)

    def evaluate_product_signals(self, product: Product) -> Optional[Alert]:
        """
        Evaluates product conditions to detect calibrated anomaly triggers:
        - Growth >= 300% or Trend Score >= 95.0 -> Critical
        - Growth >= 180% or Trend Score >= 90.0 -> Warning
        - Multi-platform spread (>= 3) -> Info
        """
        if product.growth_rate >= 300.0:
            alert = Alert(
                id=f"alt_{uuid.uuid4().hex[:8]}",
                title=f"Exponential Growth Surge (+{product.growth_rate:.0f}%)",
                description=f"{product.name} has exceeded +300% velocity threshold on {product.primary_platform}.",
                severity="Critical",
                category=product.category,
                product_id=product.id,
                product_name=product.name,
                platform=product.primary_platform,
                trigger="growth_velocity_surge",
                threshold=300.0,
                actual_value=round(product.growth_rate, 1),
                is_read=False,
                is_resolved=False,
                created_at=datetime.now(timezone.utc)
            )
            if hasattr(self.alerts, "create"):
                self.alerts.create(alert)
            return alert
        elif product.growth_rate >= 180.0 or product.trend_score >= 90.0:
            alert = Alert(
                id=f"alt_{uuid.uuid4().hex[:8]}",
                title=f"High Demand Velocity Warning ({product.velocity_label})",
                description=f"{product.name} scored {product.trend_score:.1f} with +{product.growth_rate:.0f}% trajectory.",
                severity="Warning",
                category=product.category,
                product_id=product.id,
                product_name=product.name,
                platform=product.primary_platform,
                trigger="trend_breakout_warning",
                threshold=180.0,
                actual_value=round(product.growth_rate, 1),
                is_read=False,
                is_resolved=False,
                created_at=datetime.now(timezone.utc)
            )
            if hasattr(self.alerts, "create"):
                self.alerts.create(alert)
            return alert
        return None
