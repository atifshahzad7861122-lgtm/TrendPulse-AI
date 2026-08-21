# Specification: Phase 1C — Full Functional QA & End-to-End Validation

## 1. Overview & Objective
Phase 1C validates that TrendPulse AI operates as a robust, fully functional application from public landing through complete authentication, workspace onboarding, dashboard analytics, product discovery & comparison, watchlist mutations, anomaly alert resolution, notifications, multi-stage report generation, data sources management, global search, and user settings.

## 2. In-Scope Areas
1. **Application Health & Core Ingestion Pipelines**:
   - Backend health probe (`GET /api/v1/health`)
   - In-memory data store integrity across operations
2. **Public Landing Page Navigation & Interactions**:
   - Navbar anchors, section scroll targets, FAQ accordions, CTA routes (`/register`, `/login`), mobile viewport responsiveness.
3. **Authentication & Session Lifecycle**:
   - Registration validation (email, password strength, terms check, duplicate email rejection).
   - Email verification (token exchange, cooldown, workspace routing).
   - Login & JWT persistence (remember me, error handling, session restore on refresh).
   - Forgot & Reset Password end-to-end token flow.
   - Protected route guards and unauthenticated redirection.
   - Clean logout and token destruction.
4. **Workspace Configuration**:
   - Workspace creation and preferences update (industry, currency, data sources).
5. **Dashboard Analytics & Telemetry**:
   - Metric summary cards, time-series charts (7d, 30d, all-time), category & platform filters, live signal stream.
6. **Product Discovery, Detail & Comparison**:
   - Debounced search, multi-field sorting, watchlist toggle synchronization, side-by-side multi-product comparison matrix.
7. **Anomaly Alerts & Notifications**:
   - Severity filtering, mark as read, resolve workflow, deep linking to product detail.
8. **Intelligence Reports & Generation**:
   - Report listing, multi-stage interactive generation workflow, CSV/JSON/Print export.
9. **Data Sources & Integrations**:
   - Connect/Disconnect toggles for TikTok, Daraz, Instagram, YouTube, Facebook with real-time health telemetry.
10. **Global Search & Keyboard Shortcuts**:
    - Query modal (`⌘K` / `Ctrl+K`), debounced cross-entity search results.
11. **Settings & Profile Management**:
    - Form inputs, toggle states, threshold sliders, and working save state.

## 3. Strict Boundary Constraints
- **PostgreSQL**: STRICTLY DEFERRED. In-memory repositories are maintained.
- **External APIs**: Simulated in-memory contracts only.
- **UI Design**: Obsidian Copper design system is preserved without unsolicited redesigns.
