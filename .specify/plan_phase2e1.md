# Phase 2E.1 Architectural Plan: FastAPI → Supabase PostgreSQL Connection

## Architecture Overview
```
FastAPI Router / Endpoint
       │
   Dependency Injection (deps.py)
       │
   Repository Interface (base.py)
       ├──> InMemoryRepository (in_memory.py) [when DATA_BACKEND=in_memory]
       └──> PostgresRepository (repositories/postgres/) [when DATA_BACKEND=postgres]
                 │
            AsyncSession (db/session.py)
                 │
           AsyncEngine (db/connection.py with asyncpg pool)
                 │
         Supabase PostgreSQL
```

## Implementation Modules
1. `backend/app/core/config.py`: Add `DATABASE_URL`, `SUPABASE_PROJECT_ID`, `DATA_BACKEND`, `DB_POOL_*`.
2. `backend/app/db/connection.py`: Async engine manager with asyncpg protocol normalization and pooling.
3. `backend/app/db/session.py`: Async session factory (`async_sessionmaker`).
4. `backend/app/db/dependencies.py`: Request-scoped `get_db_session` FastAPI dependency.
5. `backend/app/db/models.py`: Declarative SQLAlchemy models.
6. `backend/app/repositories/postgres/`: Concrete repository implementations backed by PostgreSQL.
7. `backend/app/api/deps.py`: Mode-aware repository resolution.
8. `backend/app/api/v1/endpoints/health.py`: Database health check endpoint.
9. `backend/tests/`: Unit & opt-in integration tests.
