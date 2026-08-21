# Phase 2E.2 Architectural Plan: Real Authentication & User Persistence

## 1. Authentication Data Architecture
```
                                ┌────────────────────────────────────────┐
                                │             FastAPI Router             │
                                │   POST /register, /login, /logout, ... │
                                └───────────────────┬────────────────────┘
                                                    │
                                        ┌───────────▼───────────┐
                                        │      AuthService      │
                                        └───────────┬───────────┘
                                                    │
                   ┌────────────────────────────────┴────────────────────────────────┐
                   │                                                                 │
         ┌─────────▼─────────┐                                             ┌─────────▼─────────┐
         │ In-Memory Backend │                                             │ PostgreSQL Engine │
         │   (DATA_BACKEND   │                                             │   (DATA_BACKEND   │
         │   = 'in_memory')  │                                             │   = 'postgres')   │
         └───────────────────┘                                             └─────────┬─────────┘
                                                                                     │
                       ┌─────────────────────────────────────────────────────────────┼──────────────────────────────────┐
                       │                                                             │                                  │
               ┌───────▼───────┐                                             ┌───────▼───────┐                  ┌───────▼───────┐
               │     users     │                                             │  workspaces   │                  │ user_sessions │
               │ user_settings │                                             │  & members    │                  │ & login_events│
               └───────────────┘                                             └───────────────┘                  └───────────────┘
```

## 2. Table Schemas Handled
1. `users`: User identity, password hash, status flags, timestamps.
2. `workspaces`: User workspace container.
3. `workspace_members`: Workspace role and membership mapping.
4. `user_settings`: User notification and dashboard preferences.
5. `user_sessions`: JWT session token hash, revocation flag, expiration.
6. `email_verifications`: Single-use email verification tokens.
7. `password_reset_tokens`: Single-use password reset tokens with 1-hour expiration.
8. `login_events`: Audit history for authentication events.
