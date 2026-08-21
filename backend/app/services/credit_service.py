import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from backend.app.models.domain import CreditAccount, CreditTransaction, CreditUsage
from backend.app.repositories.base import CreditRepository

class CreditService:
    def __init__(self, credit_repo: CreditRepository):
        self.credit_repo = credit_repo

    def get_balance(self, user_id: str) -> CreditAccount:
        return self.credit_repo.get_or_create_account(user_id)

    def check_sufficient_credits(self, user_id: str, amount: int) -> bool:
        if amount <= 0:
            return True
        acc = self.get_balance(user_id)
        return acc.current_balance >= amount

    def grant_credits(
        self,
        user_id: str,
        amount: int,
        reason: str,
        reference_type: Optional[str] = "admin_grant",
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditTransaction:
        if amount <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grant amount must be positive")

        acc = self.credit_repo.get_or_create_account(user_id)
        balance_before = acc.current_balance
        balance_after = balance_before + amount

        self.credit_repo.update_account_balance(
            user_id=user_id,
            new_balance=balance_after,
            delta_granted=amount,
            delta_used=0
        )

        now = datetime.now(timezone.utc)
        tx = CreditTransaction(
            id=f"tx_{uuid.uuid4().hex[:8]}",
            credit_account_id=acc.id,
            user_id=user_id,
            amount=amount,
            transaction_type="grant",
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=reference_type,
            reference_id=reference_id,
            description=reason,
            metadata_json=metadata or {},
            created_at=now
        )
        return self.credit_repo.create_transaction(tx)

    def consume_credits(
        self,
        user_id: str,
        amount: int,
        feature: str,
        action: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditTransaction:
        if amount <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credit consumption amount must be positive")

        # 1. Idempotency Check: if reference specified, check if already charged
        if reference_type and reference_id:
            existing_tx = self.credit_repo.get_transaction_by_reference(
                user_id=user_id,
                reference_type=reference_type,
                reference_id=reference_id
            )
            if existing_tx:
                return existing_tx

        # 2. Balance Verification
        acc = self.credit_repo.get_or_create_account(user_id)
        if acc.current_balance < amount:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits: required {amount}, current balance {acc.current_balance}"
            )

        balance_before = acc.current_balance
        balance_after = balance_before - amount

        # 3. Update Balance
        self.credit_repo.update_account_balance(
            user_id=user_id,
            new_balance=balance_after,
            delta_granted=0,
            delta_used=amount
        )

        now = datetime.now(timezone.utc)

        # 4. Record Usage
        usage = CreditUsage(
            id=f"use_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            credit_account_id=acc.id,
            feature=feature,
            action=action,
            credits_used=amount,
            reference_type=reference_type,
            reference_id=reference_id,
            metadata_json=metadata or {},
            created_at=now
        )
        self.credit_repo.record_usage(usage)

        # 5. Record Transaction
        tx = CreditTransaction(
            id=f"tx_{uuid.uuid4().hex[:8]}",
            credit_account_id=acc.id,
            user_id=user_id,
            amount=-amount,
            transaction_type="usage",
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=reference_type,
            reference_id=reference_id,
            description=f"Consumed {amount} credits for {feature} ({action})",
            metadata_json=metadata or {},
            created_at=now
        )
        return self.credit_repo.create_transaction(tx)

    def refund_credits(
        self,
        user_id: str,
        amount: int,
        reason: str,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditTransaction:
        if amount <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refund amount must be positive")

        acc = self.credit_repo.get_or_create_account(user_id)
        balance_before = acc.current_balance
        balance_after = balance_before + amount

        self.credit_repo.update_account_balance(
            user_id=user_id,
            new_balance=balance_after,
            delta_granted=0,
            delta_used=-amount
        )

        now = datetime.now(timezone.utc)
        tx = CreditTransaction(
            id=f"tx_{uuid.uuid4().hex[:8]}",
            credit_account_id=acc.id,
            user_id=user_id,
            amount=amount,
            transaction_type="refund",
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type="refund",
            reference_id=reference_id,
            description=reason,
            metadata_json=metadata or {},
            created_at=now
        )
        return self.credit_repo.create_transaction(tx)

    def adjust_credits(
        self,
        user_id: str,
        amount: int,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditTransaction:
        if amount == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Adjustment amount cannot be zero")

        acc = self.credit_repo.get_or_create_account(user_id)
        balance_before = acc.current_balance
        balance_after = balance_before + amount

        if balance_after < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Adjustment of {amount} would cause negative balance (current: {balance_before})"
            )

        delta_granted = amount if amount > 0 else 0
        delta_used = -amount if amount < 0 else 0

        self.credit_repo.update_account_balance(
            user_id=user_id,
            new_balance=balance_after,
            delta_granted=delta_granted,
            delta_used=delta_used
        )

        now = datetime.now(timezone.utc)
        tx = CreditTransaction(
            id=f"tx_{uuid.uuid4().hex[:8]}",
            credit_account_id=acc.id,
            user_id=user_id,
            amount=amount,
            transaction_type="adjustment",
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type="manual_adjustment",
            reference_id=None,
            description=reason,
            metadata_json=metadata or {},
            created_at=now
        )
        return self.credit_repo.create_transaction(tx)

    def get_transaction_history(self, user_id: str, limit: int = 50, offset: int = 0) -> List[CreditTransaction]:
        return self.credit_repo.list_transactions(user_id=user_id, limit=limit, offset=offset)

    def get_usage_history(self, user_id: str, limit: int = 50, offset: int = 0) -> List[CreditUsage]:
        return self.credit_repo.list_usage(user_id=user_id, limit=limit, offset=offset)
