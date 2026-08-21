from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from backend.app.models.domain import User
from backend.app.api.deps import get_current_user, get_credit_service
from backend.app.services.credit_service import CreditService
from backend.app.schemas.credits import (
    CreditAccountResponse, CreditTransactionResponse, CreditUsageResponse
)
from backend.app.schemas.common import ResponseModel

router = APIRouter()

@router.get("/balance", response_model=ResponseModel[CreditAccountResponse])
def get_credit_balance(
    current_user: User = Depends(get_current_user),
    credit_service: CreditService = Depends(get_credit_service)
):
    acc = credit_service.get_balance(current_user.id)
    return ResponseModel(
        success=True,
        message="Credit balance retrieved successfully",
        data=CreditAccountResponse(
            id=acc.id,
            user_id=acc.user_id,
            current_balance=acc.current_balance,
            lifetime_granted=acc.lifetime_granted,
            lifetime_used=acc.lifetime_used,
            updated_at=acc.updated_at
        )
    )

@router.get("/transactions", response_model=ResponseModel[List[CreditTransactionResponse]])
def get_transaction_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    credit_service: CreditService = Depends(get_credit_service)
):
    txs = credit_service.get_transaction_history(current_user.id, limit=limit, offset=offset)
    return ResponseModel(
        success=True,
        message="Credit transactions retrieved successfully",
        data=[
            CreditTransactionResponse(
                id=t.id,
                amount=t.amount,
                transaction_type=t.transaction_type,
                balance_before=t.balance_before,
                balance_after=t.balance_after,
                reference_type=t.reference_type,
                reference_id=t.reference_id,
                description=t.description,
                created_at=t.created_at
            )
            for t in txs
        ]
    )

@router.get("/usage", response_model=ResponseModel[List[CreditUsageResponse]])
def get_usage_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    credit_service: CreditService = Depends(get_credit_service)
):
    usages = credit_service.get_usage_history(current_user.id, limit=limit, offset=offset)
    return ResponseModel(
        success=True,
        message="Credit usage history retrieved successfully",
        data=[
            CreditUsageResponse(
                id=u.id,
                feature=u.feature,
                action=u.action,
                credits_used=u.credits_used,
                reference_type=u.reference_type,
                reference_id=u.reference_id,
                created_at=u.created_at
            )
            for u in usages
        ]
    )
