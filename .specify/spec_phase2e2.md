# Phase 2E.2 Specification: Real Authentication & User Persistence

## 1. Goal & Objectives
Connect the existing FastAPI JWT + bcrypt authentication system to PostgreSQL/Supabase, guaranteeing persistent user accounts, session tracking, atomic registration transactions, email verification tokens, one-time password reset tokens, and audit login event logging.

## 2. Requirements & Constraints
- **Preserve Frontend Architecture**: Zero breaking changes to React auth routes (`/login`, `/register`, `/verify-email`, `/forgot-password`, `/reset-password`) or JSON API contracts.
- **Stateless JWT with Stateful Session Tracking**: FastAPI JWT handles stateless token decoding, while `user_sessions` provides revocation, concurrency management, and audit tracking.
- **Atomic Operations**: Registration atomically creates `users` + `workspaces` + `workspace_members` + `user_settings` + `email_verifications`.
- **Security & Privacy**:
  - Passwords hashed with bcrypt (72-byte truncation safe).
  - No credentials, passwords, or raw tokens in logs or API responses.
  - Forgot password endpoint does not leak user account existence.
  - Reset tokens and verification tokens are single-use with expiration timestamps.
- **Audit Logging**: `login_events` captures `login_success`, `login_failed`, `logout`, `password_reset`, and `email_verified`.
- **Testing**:
  - 100% pass on all unit & integration tests.
  - Opt-in live Supabase test with automatic cleanup.
