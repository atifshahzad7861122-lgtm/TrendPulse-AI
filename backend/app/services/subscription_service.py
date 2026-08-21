import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from backend.app.models.domain import SubscriptionPlan, UserSubscription, CreditTransaction
from backend.app.repositories.base import SubscriptionRepository
from backend.app.services.credit_service import CreditService

class SubscriptionService:
    def __init__(
        self,
        subscription_repo: SubscriptionRepository,
        credit_service: CreditService
    ):
        self.subscription_repo = subscription_repo
        self.credit_service = credit_service

    def list_plans(self, active_only: bool = True) -> List[SubscriptionPlan]:
        return self.subscription_repo.list_plans(active_only=active_only)

    def get_plan_by_id(self, plan_id: str) -> Optional[SubscriptionPlan]:
        return self.subscription_repo.get_plan_by_id(plan_id)

    def get_plan_by_slug(self, slug: str) -> Optional[SubscriptionPlan]:
        return self.subscription_repo.get_plan_by_slug(slug)

    def get_user_subscription(self, user_id: str) -> UserSubscription:
        sub = self.subscription_repo.get_user_subscription(user_id)
        if sub:
            return sub

        # Fallback: create default active Free subscription
        free_plan = self.subscription_repo.get_plan_by_slug("free")
        plan_id = free_plan.id if free_plan else "plan_free"
        now = datetime.now(timezone.utc)
        default_sub = UserSubscription(
            id=f"sub_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            plan_id=plan_id,
            status="active",
            started_at=now,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            created_at=now,
            updated_at=now
        )
        self.subscription_repo.create_user_subscription(default_sub)
        return default_sub

    def change_subscription(self, user_id: str, new_plan_slug: str) -> UserSubscription:
        target_plan = self.subscription_repo.get_plan_by_slug(new_plan_slug)
        if not target_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription plan '{new_plan_slug}' not found"
            )

        now = datetime.now(timezone.utc)
        sub = self.get_user_subscription(user_id)
        sub.plan_id = target_plan.id
        sub.status = "active"
        sub.cancelled_at = None
        sub.current_period_start = now
        sub.current_period_end = now + timedelta(days=30)
        sub.updated_at = now

        updated_sub = self.subscription_repo.update_user_subscription(sub)

        # Allocate credits for new plan (idempotent for this period)
        period_key = f"{now.strftime('%Y-%m-%d')}_{target_plan.slug}"
        self.allocate_monthly_credits(user_id, period_key=period_key)

        return updated_sub

    def cancel_subscription(self, user_id: str) -> UserSubscription:
        sub = self.get_user_subscription(user_id)
        sub.status = "cancelled"
        sub.cancelled_at = datetime.now(timezone.utc)
        return self.subscription_repo.update_user_subscription(sub)

    def allocate_monthly_credits(
        self,
        user_id: str,
        period_key: Optional[str] = None
    ) -> Optional[CreditTransaction]:
        sub = self.get_user_subscription(user_id)
        plan = self.subscription_repo.get_plan_by_id(sub.plan_id)
        if not plan:
            plan = self.subscription_repo.get_plan_by_slug("free")
        if not plan or plan.monthly_credits <= 0:
            return None

        # Derive period key if not supplied
        if not period_key:
            period_key = f"{sub.current_period_start.strftime('%Y-%m')}_{plan.slug}"

        # Idempotent grant via reference tagging
        return self.credit_service.grant_credits(
            user_id=user_id,
            amount=plan.monthly_credits,
            reason=f"Monthly credit allocation for {plan.name} plan",
            reference_type="subscription_period",
            reference_id=period_key,
            metadata={"plan_name": plan.name, "plan_id": plan.id, "period_key": period_key}
        )
