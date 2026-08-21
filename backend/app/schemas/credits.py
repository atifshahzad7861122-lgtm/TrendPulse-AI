from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class CreditAccountResponse(BaseModel):
    id: str
    user_id: str
    current_balance: int
    lifetime_granted: int
    lifetime_used: int
    updated_at: datetime

class CreditTransactionResponse(BaseModel):
    id: str
    amount: int
    transaction_type: str
    balance_before: int
    balance_after: int
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    description: str
    created_at: datetime

class CreditUsageResponse(BaseModel):
    id: str
    feature: str
    action: str
    credits_used: int
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    created_at: datetime

class SubscriptionPlanResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    price: float
    currency: str
    billing_interval: str
    monthly_credits: int
    is_active: bool
    features: List[str] = Field(default_factory=list)
    limits: Dict[str, Any] = Field(default_factory=dict)

class UserSubscriptionResponse(BaseModel):
    id: str
    user_id: str
    plan_id: str
    plan_name: Optional[str] = None
    plan_slug: Optional[str] = None
    status: str
    started_at: datetime
    current_period_start: datetime
    current_period_end: datetime
    cancelled_at: Optional[datetime] = None
    monthly_credits: Optional[int] = None

class ChangeSubscriptionRequest(BaseModel):
    plan_slug: str
