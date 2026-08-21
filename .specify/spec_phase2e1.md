# Phase 2E.1 Specification: FastAPI → Supabase PostgreSQL Connection

## 1. Goal & Objectives
Connect the existing FastAPI backend of TrendPulse AI to the Supabase PostgreSQL database using an asynchronous SQLAlchemy 2.x engine and connection pooling, while keeping existing in-memory repository abstractions intact for development and local testing.

## 2. Requirements & Constraints
- **Zero Frontend Mutation**: No redesigns or route changes in the React frontend.
- **Repository Interface Decoupling**: Service layer (`ProductIntelligenceEngine`, `CategoryService`, `AlertService`, etc.) must remain decoupled from database implementations via abstract repository interfaces.
- **Dual Mode Support**:
  - `DATA_BACKEND=in_memory` (default for CI / local test runs)
  - `DATA_BACKEND=postgres` (production / Supabase PostgreSQL)
- **Database Safety**:
  - No destructive migrations.
  - No plaintext credentials in logs or responses.
  - Request-safe sessions with automated rollback on exception and guaranteed closure.
- **Health Check Endpoint**:
  - `GET /api/v1/health/database`
- **Testing**:
  - Unit tests for session lifecycle, health check, and repository selection.
  - Opt-in Supabase integration test guarded by `SUPABASE_INTEGRATION_TEST=true`.
  - All existing backend tests (73+) must pass.
