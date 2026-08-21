# TrendPulse AI: Full Frontend Functionality & FastAPI Integration (Database Deferred)
## Phase 1B Specification Document

### 1. Executive Summary & Goal
The objective of Phase 1B is to convert the approved TrendPulse AI UI screens (designed and finalized in Stitch) into a 100% fully functional web application powered by a real FastAPI backend, while explicitly deferring persistent database storage (PostgreSQL) by utilizing structured in-memory repository abstractions.

Every button, link, form, dropdown, tab, modal, filter, search, chart interaction, action trigger, and pagination control across the application must be active and wired to FastAPI endpoints or real client routing states.

---

### 2. Scope & Boundaries

#### In Scope
- **Frontend Architecture:** Modern React + TypeScript + Vite + Tailwind CSS + Lucide Icons / Material Symbols + Recharts / Lucide UI + React Router DOM v6.
- **Visual Design Integrity:** 100% preservation of the approved "Obsidian Copper" dark theme (`#121411` background, `#df7328` / `#ffb68d` copper/orange accents, Hanken Grotesk, Geist, EB Garamond typography, glassmorphism containers).
- **Centralized API Client:** Unified typed API client (`/src/services/api.ts`) and modular domain services (`authService`, `workspaceService`, `productService`, `categoryService`, `platformService`, `reportService`, `watchlistService`, `alertService`, `dataSourceService`, `searchService`, `notificationService`, `settingsService`).
- **FastAPI Backend (`/api/v1`):** Complete REST API implemented in Python FastAPI with Pydantic v2 validation models.
- **In-Memory Repository Pattern:** Repository interfaces with in-memory implementations (`InMemoryUserRepository`, `InMemoryWorkspaceRepository`, `InMemoryProductRepository`, `InMemoryCategoryRepository`, `InMemoryPlatformRepository`, `InMemoryWatchlistRepository`, `InMemoryAlertRepository`, `InMemoryNotificationRepository`, `InMemoryReportRepository`, `InMemoryDataSourceRepository`, `InMemorySettingsRepository`).
- **Comprehensive Page Functionality:**
  1. Public Landing Page (`/`): Dynamic hero signals, interactive ticker, category showcase, features, interactive FAQ, live preview, smooth navigation anchors (`#product`, `#intelligence`, `#how-it-works`, `#data-sources`, `#reports`), CTAs to `/register` and `/login`.
  2. Authentication & Onboarding:
     - Sign Up (`/register`): Validation, email verification redirect with dev-safe token.
     - Email Verification (`/verify-email`): Token validation, resend timer, error/success states, continue to workspace setup.
     - Sign In (`/login`): Validation, temporary JWT token generation, route guard.
     - Forgot Password (`/forgot-password`): Request reset token with dev-safe link.
     - Reset Password (`/reset-password`): Token check, password strength criteria, confirmation.
     - Workspace Setup (`/workspace-setup`): Step-by-step onboarding (workspace name, industry, use case, currency, initial data sources) -> redirects to `/dashboard`.
  3. Core Application (Protected Layout):
     - Dashboard (`/dashboard`): Real KPI cards (Trending Products, Total Signals, Top Velocity, Alert Index), timeframe filter (7D, 30D, All Time), Category & Platform filtering, real-time trend chart, top surge products, live signal feed, Quick Export & Generate Report action.
     - Products (`/products`): Multi-criteria search, category filters, platform filters, sorting (velocity, volume, growth), product cards/table view, toggle watchlist action, click to detail.
     - Product Detail (`/products/:id`): Deep-dive trend velocity, volume charts, AI synthesis summaries, platform breakdowns (Daraz, TikTok, YouTube, Instagram), historical pricing, related products, watchlist toggle.
     - Product Comparison (`/product-comparison`): Select 2-4 products, side-by-side metric matrix, overlapping trend velocity charts, platform share comparison.
     - Categories (`/categories`): Category cards with live velocity indicators, product counts, top products per category, filtering & search.
     - Platforms (`/platforms`): Performance breakdown across TikTok, Daraz, Instagram, YouTube, Facebook, platform share metrics, recent high-velocity spikes.
     - Watchlist (`/watchlist`): Filtered user watchlist, instant remove/add, alert threshold configuration, bulk export.
     - Alerts & Notifications (`/alerts`, `/notifications`): Real alert triggers, mark as read, resolve, filter by severity (Critical, Warning, Info), direct link to offending product.
     - Reports & Generation (`/reports`, `/report-generation`, `/reports/:id`): Report library, multi-step report generation flow with realistic pipeline states ("Preparing report..." -> "Analyzing signals..." -> "Building report..." -> "Report ready"), full report viewer with export (JSON/CSV/PDF-print).
     - Data Sources (`/data-sources`): Simulated OAuth connect/disconnect for Daraz, TikTok, Instagram, YouTube, Facebook, sync frequency, connection health status.
     - Global Search (`/search` or Command-K modal): Cross-entity instant search (Products, Categories, Platforms, Reports, Alerts).
     - Settings (`/settings`): Tabbed settings (Profile, Workspace, Notifications, AI Preferences, Data Source Sync, Display/Theme) with working Save Changes, feedback toasts, validation.
- **State Management & UI States:** All data screens feature explicit Loading Skeleton, Error Banner with retry, and Empty State handling.
- **Testing:** Comprehensive backend pytest test suite and frontend verification tests.

#### Out of Scope (Deferred to Future Phases)
- **PostgreSQL Database & Alembic Migrations:** Strictly deferred. Repositories operate purely in-memory.
- **External Third-Party API Integrations:** No live calls to external TikTok/Daraz/YouTube APIs; state is managed through realistic simulated in-memory feeds.
- **Alibaba Cloud Qwen / Sentence Transformers / StatsForecast Integration:** Advanced AI models will be plugged in Phase 2; the current backend generates realistic analytical heuristics conforming to the exact AI schema contracts.

---

### 3. Architecture & Repository Abstraction

```
[Frontend UI (React + Tailwind)]
         │
         ▼  (HTTP / REST JSON)
[Central API Client (/src/services/api.ts)]
         │
         ▼
[FastAPI REST Layer (/api/v1/*)]
         │
         ▼
[Business Service Layer (/backend/services/*)]
         │
         ▼
[Repository Interfaces (Abstract Base Classes)]
         │
         ├─── (Current Phase 1B) ──► [In-Memory Repositories (/backend/repositories/in_memory/*)]
         └─── (Future Phase 2)  ──► [PostgreSQL Repositories (/backend/repositories/postgres/*)]
```

### 4. API Endpoints Specification (`/api/v1`)

| Domain | Method | Endpoint | Description |
|---|---|---|---|
| **Health** | GET | `/health` | System health check |
| **Auth** | POST | `/auth/register` | User registration |
| | POST | `/auth/login` | User login & token issuance |
| | POST | `/auth/logout` | User logout |
| | POST | `/auth/verify-email` | Verify email token |
| | POST | `/auth/forgot-password` | Request password reset token |
| | POST | `/auth/reset-password` | Set new password with token |
| | GET | `/auth/me` | Current authenticated user profile |
| **Workspace** | GET | `/workspace` | Get active workspace details |
| | PUT | `/workspace` | Update workspace configuration |
| | POST | `/workspace/setup` | Initial workspace onboarding |
| **Dashboard** | GET | `/dashboard/metrics` | KPI summary cards |
| | GET | `/dashboard/trends` | Time-series chart points (7D/30D/All) |
| | GET | `/dashboard/feed` | Real-time signal stream |
| **Products** | GET | `/products` | List & filter products (search, category, platform, sort) |
| | GET | `/products/{id}` | Detailed product intelligence |
| | GET | `/products/compare` | Compare multiple products |
| **Categories** | GET | `/categories` | List market categories with velocity scores |
| | GET | `/categories/{id}` | Category detail & product list |
| **Platforms** | GET | `/platforms` | Multi-platform analytics & share metrics |
| **Watchlist** | GET | `/watchlist` | List user watchlisted products |
| | POST | `/watchlist/{product_id}` | Add product to watchlist |
| | DELETE | `/watchlist/{product_id}` | Remove product from watchlist |
| **Alerts** | GET | `/alerts` | List system alerts |
| | POST | `/alerts/{id}/read` | Mark alert as read |
| | POST | `/alerts/{id}/resolve`| Resolve alert |
| **Notifications** | GET | `/notifications` | List user notifications |
| | POST | `/notifications/read-all`| Mark all notifications read |
| **Reports** | GET | `/reports` | List generated intelligence reports |
| | POST | `/reports/generate` | Trigger async/stepped report generation |
| | GET | `/reports/{id}` | Get report detail |
| | GET | `/reports/{id}/export` | Export report data |
| **Data Sources**| GET | `/data-sources` | List data source integration statuses |
| | POST | `/data-sources/{id}/connect` | Connect data source |
| | POST | `/data-sources/{id}/disconnect` | Disconnect data source |
| **Search** | GET | `/search` | Global cross-entity search |
| **Settings** | GET | `/settings` | Retrieve user/workspace settings |
| | PUT | `/settings` | Save updated settings |

---

### 5. Quality, Performance & Compliance Acceptance Criteria
1. Frontend build (`npm run build`) runs with zero TypeScript or Vite bundle errors.
2. Backend starts cleanly with `uvicorn main:app` and exposes interactive OpenAPI docs at `/docs`.
3. Pytest backend test suite passes 100% of functional test cases.
4. No dead buttons, unhandled links, blank screens, or fake frontend-only mutations.
5. Absolute fidelity to the approved Obsidian Copper UI theme and responsive breakpoints.
