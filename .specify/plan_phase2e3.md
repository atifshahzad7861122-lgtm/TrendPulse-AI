# Phase 2E.3 Architectural Plan: Credit & Subscription Engine

## 1. Domain Models & DB ORM
- Domain models in `backend/app/models/domain.py`:
  - `SubscriptionPlan`
  - `UserSubscription`
  - `CreditAccount`
  - `CreditTransaction`
  - `CreditUsage`
- SQLAlchemy ORM models in `backend/app/db/models.py`:
  - `SubscriptionPlanModel` (`subscription_plans`)
  - `UserSubscriptionModel` (`user_subscriptions`)
  - `CreditAccountModel` (`credit_accounts`)
  - `CreditTransactionModel` (`credit_transactions`)
  - `CreditUsageModel` (`credit_usage`)

## 2. Repositories Layer
- Define interfaces in `backend/app/repositories/base.py`:
  - `SubscriptionRepository`
  - `CreditRepository`
- In-Memory implementation in `backend/app/repositories/in_memory.py`:
  - `InMemorySubscriptionRepository` with thread safety (`threading.RLock`) and standard plan seeds.
  - `InMemoryCreditRepository` with thread safety (`threading.RLock`).
- PostgreSQL async implementation in `backend/app/repositories/postgres/__init__.py`:
  - `PostgresSubscriptionRepository`
  - `PostgresCreditRepository`

## 3. Services Layer
- `CreditService` in `backend/app/services/credit_service.py`:
  - `get_balance(user_id)`
  - `grant_credits(user_id, amount, reason, metadata)`
  - `consume_credits(user_id, amount, feature, action, reference_type, reference_id, metadata)`
  - `refund_credits(user_id, amount, reason, reference_id, metadata)`
  - `adjust_credits(user_id, amount, reason, metadata)`
  - `get_transaction_history(user_id, limit, offset)`
  - `get_usage_history(user_id, limit, offset)`
  - `check_sufficient_credits(user_id, amount)`
- `SubscriptionService` in `backend/app/services/subscription_service.py`:
  - `list_plans()`
  - `get_user_subscription(user_id)`
  - `change_subscription(user_id, new_plan_slug)`
  - `cancel_subscription(user_id)`
  - `allocate_monthly_credits(user_id, period_key)`

## 4. Endpoints & Dependency Injection
- Schemas in `backend/app/schemas/credits.py`:
  - `CreditAccountResponse`, `CreditTransactionResponse`, `CreditUsageResponse`
  - `SubscriptionPlanResponse`, `UserSubscriptionResponse`, `ChangeSubscriptionRequest`
- Endpoints in `backend/app/api/v1/endpoints/credits.py` and `subscription.py`.
- Wire routes in `backend/app/api/v1/router.py` and dependencies in `backend/app/api/deps.py`.
- Integrate default Free tier allocation in `AuthService.register()`.

## 5. Verification & Tests
- `backend/tests/test_credits_and_subscriptions.py` covering all 26 lifecycle and invariant requirements including concurrency race prevention.
- Update `backend/tests/test_supabase_integration.py` for live opt-in checks.
- Full pytest suite verification.
- Frontend lint and production build.
