# Phase 2E.3 Specification: Production Credit & Subscription Engine

## 1. Objective
Implement a robust, persistent, database-backed subscription and credit accounting system for TrendPulse AI using dual-mode persistence (`in_memory` and Supabase PostgreSQL `postgres`).

## 2. Key Architecture Requirements
- **Dedicated Credit Accounts**: 1-to-1 relationship between `User` and `CreditAccount`.
- **Immutable Transaction Ledger**: Every credit change creates a `CreditTransaction` recording `balance_before`, `balance_after`, `transaction_type`, and reference telemetry.
- **Granular Credit Usage**: Dedicated `CreditUsage` table logging the consuming feature, action, and reference identifiers.
- **Strict Invariants**:
  - `current_balance >= 0` enforced at repository and domain level.
  - Transactions must be atomic: usage + transaction + balance update or total rollback.
- **Idempotency**: Retrying credit consumption with identical `(reference_type, reference_id)` returns existing record without double-charging.
- **Concurrency Safety**: Thread-safe locking in-memory and row-level locking / atomic transactions in PostgreSQL to prevent race conditions.
- **Subscription Management**:
  - Configurable plans: Free, Pro, Business, Enterprise.
  - Active subscription tracking: status, period boundaries, cancellation timestamps.
  - Idempotent monthly credit allocation with period reference tagging.
- **Security & Authorization**:
  - User identity derived strictly from validated JWT claims (`current_user.id`).
  - No direct client manipulation of credit balances or admin mutations.
  - No payment gateways or real-money charging in this phase.

## 3. Supported Plans & Default Credit Allocations
- **Free**: 100 credits / month ($0)
- **Pro**: 1,000 credits / month ($49)
- **Business**: 5,000 credits / month ($199)
- **Enterprise**: 25,000 credits / month ($599)
*(Note: Pricing values are plan metadata only; no payment processing is implemented)*

## 4. Feature Credit Costs (Baseline Defaults)
- `report_generation`: 25 credits
- `ai_analysis`: 10 credits
- `trend_prediction`: 5 credits
- `data_analysis`: 2 credits
*(Costs are configurable and applied only when approved features invoke credit consumption)*
