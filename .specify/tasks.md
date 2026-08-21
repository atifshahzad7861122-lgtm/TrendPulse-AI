# TrendPulse AI: Phase 1B Executable Tasks

## Task Group A: Project Inspection & Architecture Alignment
- [ ] Task A.1: Inspect Stitch design theme, CSS tokens, fonts, and layout variables.
- [x] Task A.1: Inspect Stitch design theme, CSS tokens, fonts, and layout variables.
- [x] Task A.2: Setup project folder structure for both `frontend/` and `backend/`.
- [x] Task A.3: Configure frontend Vite + React + TypeScript + Tailwind CSS with the Obsidian Copper theme.
- [x] Task A.4: Configure backend FastAPI app with CORS, logging, and error handling middlewares.

## Task Group B: API Client & Backend In-Memory Foundation
- [x] Task B.1: Create abstract repository interfaces (`backend/app/repositories/base.py`).
- [x] Task B.2: Implement thread-safe in-memory repositories with realistic data seeding (`backend/app/repositories/in_memory.py`).
- [x] Task B.3: Implement dependency injection providers (`backend/app/api/deps.py`).
- [x] Task B.4: Implement frontend centralized API client (`frontend/src/services/api.ts`) with request/response interceptors, error mapping, and auth token management.
- [x] Task B.5: Implement domain-specific frontend service modules.

## Task Group C: Authentication
- [x] Task C.1: Backend endpoints (`/api/v1/auth/register`, `/login`, `/logout`, `/verify-email`, `/forgot-password`, `/reset-password`, `/me`).
- [x] Task C.2: Frontend AuthContext and route protection guards.
- [x] Task C.3: Connect Create Account screen (`/register`) with field validations and redirect to verification.
- [x] Task C.4: Connect Email Verification screen (`/verify-email`) with dev token helpers, resend timer, and validation.
- [x] Task C.5: Connect Sign In screen (`/login`) with error feedback, remember me, and direct redirect.
- [x] Task C.6: Connect Forgot Password (`/forgot-password`) and Reset Password (`/reset-password`) screens.

## Task Group D: Workspace Onboarding
- [x] Task D.1: Backend workspace setup endpoints (`/api/v1/workspace`, `/api/v1/workspace/setup`).
- [x] Task D.2: Connect Workspace Setup onboarding flow (`/workspace-setup`) with industry selection, currency selection, and optional data source toggles.

## Task Group E: Dashboard
- [x] Task E.1: Backend `/api/v1/dashboard/metrics`, `/trends`, `/feed` endpoints with time range and filter support.
- [x] Task E.2: Connect Dashboard page (`/dashboard`) with real KPI cards, Recharts time-series chart, time filters (7D, 30D, All), category & platform dropdowns, and quick actions (Refresh, Quick Export, Generate Report).

## Task Group F: Products & Product Details
- [ ] Task F.1: Backend `/api/v1/products`, `/api/v1/products/{id}`, and `/api/v1/products/compare` endpoints.
- [ ] Task F.2: Connect Products catalog page (`/products`) with multi-keyword search, category filter, platform filter, sorting, and pagination.
- [ ] Task F.3: Connect Product Detail page (`/products/:id`) with velocity metrics, signal charts, platform breakdowns, AI narrative summary, related products, and watchlist toggle.

## Task Group G: Categories & Platforms
- [ ] Task G.1: Backend `/api/v1/categories` and `/api/v1/platforms` endpoints.
- [ ] Task G.2: Connect Categories page (`/categories`) with search, velocity score badges, and product counts.
- [ ] Task G.3: Connect Platforms page (`/platforms`) with multi-platform signal volume, trend indicators, and channel share analytics.

## Task Group H: Watchlist & Alerts
- [ ] Task H.1: Backend `/api/v1/watchlist` (GET, POST, DELETE) and `/api/v1/alerts` (GET, POST mark read/resolve) endpoints.
- [ ] Task H.2: Connect Watchlist page (`/watchlist`) with instant product removal, search, filtering, and export.
- [ ] Task H.3: Connect Alerts page (`/alerts`) with severity filtering, mark as read, resolve, and direct product deep link.

## Task Group I: Reports & Report Generation
- [ ] Task I.1: Backend `/api/v1/reports` and `/api/v1/reports/generate` endpoints.
- [ ] Task I.2: Connect Reports listing page (`/reports`) with search, type filter, and view report triggers.
- [ ] Task I.3: Connect multi-stage Report Generation workspace (`/report-generation`) with real progression ("Preparing report..." -> "Analyzing signals..." -> "Building report..." -> "Report ready").
- [ ] Task I.4: Connect Report Detail page (`/reports/:id`) with interactive sections, insights, and export capabilities.

## Task Group J: Data Sources
- [ ] Task J.1: Backend `/api/v1/data-sources` endpoints (GET list, POST connect, POST disconnect).
- [ ] Task J.2: Connect Data Sources page (`/data-sources`) with toggle connection states for Daraz, TikTok, Instagram, YouTube, and Facebook.

## Task Group K: Global Search & Notifications
- [ ] Task K.1: Backend `/api/v1/search` cross-domain search endpoint and `/api/v1/notifications` endpoints.
- [ ] Task K.2: Connect Global Search command center (`/search` and header search) with grouped results and instant routing.
- [ ] Task K.3: Connect Notifications dropdown / drawer with mark all as read and item dismissal.

## Task Group L: Settings & Product Comparison
- [ ] Task L.1: Backend `/api/v1/settings` (GET, PUT) endpoints.
- [ ] Task L.2: Connect Settings page (`/settings`) with profile, workspace, notifications, AI preferences, data source preferences, and display settings.
- [ ] Task L.3: Connect Product Comparison page (`/product-comparison`) with dynamic product pickers, multi-chart comparison, and feature matrix.

## Task Group M: Animations, Loading, Empty & Error States
- [ ] Task M.1: Implement global toast notification system (`ToastContext`).
- [ ] Task M.2: Implement uniform Skeleton loaders, Empty State illustrations, and Error Boundaries with retry buttons across all data views.
- [ ] Task M.3: Audit all micro-interactions, button hover states, modal animations, and responsive layouts across Desktop, Tablet, and Mobile.

## Task Group N: End-to-End Validation & Testing
- [ ] Task N.1: Create and execute backend test suite (`pytest`) covering all auth, workspace, product, report, and settings endpoints.
- [ ] Task N.2: Verify frontend production build (`npm run build`).
- [ ] Task N.3: Validate complete end-to-end user journey from Landing Page through Registration, Verification, Workspace Setup, Dashboard, Products, Watchlist, Reports, Alerts, Settings, and Logout.
