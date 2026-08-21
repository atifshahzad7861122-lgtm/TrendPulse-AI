# Phase 2E.3 Tasks: Production Credit & Subscription Engine

## 1. Domain Models & DB ORM
- [x] Task 1.1: Add domain models in `backend/app/models/domain.py` (`SubscriptionPlan`, `UserSubscription`, `CreditAccount`, `CreditTransaction`, `CreditUsage`).
- [x] Task 1.2: Add SQLAlchemy ORM models in `backend/app/db/models.py` for subscription and credit tables with indexes and constraints.

## 2. Repositories Layer
- [x] Task 2.1: Define `SubscriptionRepository` and `CreditRepository` interfaces in `backend/app/repositories/base.py`.
- [x] Task 2.2: Implement thread-safe `InMemorySubscriptionRepository` and `InMemoryCreditRepository` in `backend/app/repositories/in_memory.py`.
- [x] Task 2.3: Implement async PostgreSQL persistence in `backend/app/repositories/postgres/__init__.py`.

## 3. Services Layer
- [x] Task 3.1: Create `CreditService` in `backend/app/services/credit_service.py` with balance checks, transactional deductions, idempotency by reference, refunds, and adjustments.
- [x] Task 3.2: Create `SubscriptionService` in `backend/app/services/subscription_service.py` with plan queries, subscription switching, cancellation, and idempotent monthly credit allocation.
- [x] Task 3.3: Hook automatic Free tier subscription and initial credit allocation into `AuthService.register()`.

## 4. Endpoints & Wiring
- [x] Task 4.1: Create request/response schemas in `backend/app/schemas/credits.py`.
- [x] Task 4.2: Implement endpoints in `backend/app/api/v1/endpoints/credits.py` and `subscription.py`.
- [x] Task 4.3: Mount routers in `backend/app/api/v1/router.py` and configure providers in `backend/app/api/deps.py`.

## 5. Testing & Validation
- [x] Task 5.1: Create `backend/tests/test_credits_and_subscriptions.py` covering credit lifecycles, negative balance prevention, idempotency, and concurrent deductions (11/11 passed).
- [x] Task 5.2: Update `backend/tests/test_supabase_integration.py` for credit and subscription table verification.
- [x] Task 5.3: Run full backend test suite (`pytest -v` -> 100 passed, 4 skipped, 0 failures).
- [x] Task 5.4: Run frontend lint & build (`npm run lint` -> 0 errors, `npm run build` -> PASS).
- [x] Task 5.5: Generate `walkthrough.md` and Phase 2E.3 Implementation Report.
