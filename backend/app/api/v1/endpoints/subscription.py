from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.models.domain import User
from backend.app.api.deps import get_current_user, get_subscription_service
from backend.app.services.subscription_service import SubscriptionService
from backend.app.schemas.credits import (
    SubscriptionPlanResponse, UserSubscriptionResponse, ChangeSubscriptionRequest
)
from backend.app.schemas.common import ResponseModel

router = APIRouter()

@router.get("", response_model=ResponseModel[UserSubscriptionResponse])
def get_user_subscription(
    current_user: User = Depends(get_current_user),
    sub_service: SubscriptionService = Depends(get_subscription_service)
):
    sub = sub_service.get_user_subscription(current_user.id)
    plan = sub_service.get_plan_by_id(sub.plan_id)
    return ResponseModel(
        success=True,
        message="Active subscription retrieved successfully",
        data=UserSubscriptionResponse(
            id=sub.id,
            user_id=sub.user_id,
            plan_id=sub.plan_id,
            plan_name=plan.name if plan else "Free",
            plan_slug=plan.slug if plan else "free",
            status=sub.status,
            started_at=sub.started_at,
            current_period_start=sub.current_period_start,
            current_period_end=sub.current_period_end,
            cancelled_at=sub.cancelled_at,
            monthly_credits=plan.monthly_credits if plan else 100
        )
    )

@router.get("/plans", response_model=ResponseModel[List[SubscriptionPlanResponse]])
def list_subscription_plans(
    sub_service: SubscriptionService = Depends(get_subscription_service)
):
    plans = sub_service.list_plans(active_only=True)
    return ResponseModel(
        success=True,
        message="Subscription plans retrieved successfully",
        data=[
            SubscriptionPlanResponse(
                id=p.id,
                name=p.name,
                slug=p.slug,
                description=p.description,
                price=p.price,
                currency=p.currency,
                billing_interval=p.billing_interval,
                monthly_credits=p.monthly_credits,
                is_active=p.is_active,
                features=p.features,
                limits=p.limits
            )
            for p in plans
        ]
    )

@router.post("/change", response_model=ResponseModel[UserSubscriptionResponse])
def change_subscription(
    req: ChangeSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    sub_service: SubscriptionService = Depends(get_subscription_service)
):
    updated_sub = sub_service.change_subscription(current_user.id, req.plan_slug)
    plan = sub_service.get_plan_by_id(updated_sub.plan_id)
    return ResponseModel(
        success=True,
        message=f"Subscription changed to {plan.name if plan else req.plan_slug} successfully",
        data=UserSubscriptionResponse(
            id=updated_sub.id,
            user_id=updated_sub.user_id,
            plan_id=updated_sub.plan_id,
            plan_name=plan.name if plan else req.plan_slug,
            plan_slug=plan.slug if plan else req.plan_slug,
            status=updated_sub.status,
            started_at=updated_sub.started_at,
            current_period_start=updated_sub.current_period_start,
            current_period_end=updated_sub.current_period_end,
            cancelled_at=updated_sub.cancelled_at,
            monthly_credits=plan.monthly_credits if plan else 100
        )
    )

@router.post("/cancel", response_model=ResponseModel[UserSubscriptionResponse])
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    sub_service: SubscriptionService = Depends(get_subscription_service)
):
    cancelled_sub = sub_service.cancel_subscription(current_user.id)
    plan = sub_service.get_plan_by_id(cancelled_sub.plan_id)
    return ResponseModel(
        success=True,
        message="Subscription has been cancelled",
        data=UserSubscriptionResponse(
            id=cancelled_sub.id,
            user_id=cancelled_sub.user_id,
            plan_id=cancelled_sub.plan_id,
            plan_name=plan.name if plan else "Unknown",
            plan_slug=plan.slug if plan else "unknown",
            status=cancelled_sub.status,
            started_at=cancelled_sub.started_at,
            current_period_start=cancelled_sub.current_period_start,
            current_period_end=cancelled_sub.current_period_end,
            cancelled_at=cancelled_sub.cancelled_at,
            monthly_credits=plan.monthly_credits if plan else 100
        )
    )
