# Implementation Plan: Phase 2A — Real Backend Business Logic

## 1. Backend Audit & Functionality Matrix
| Endpoint | Purpose | Current Implementation | Missing Logic | Repository | Service | Required Calculation | Frontend Consumer | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /dashboard/summary` | Real-time KPI cards & live signals | Hardcoded KPI multiplier & static signals | Dynamic aggregations from products & signal events | ProductRepo, AlertRepo | DashboardService | Avg velocity, volume sum, critical alerts count, top multiplier | DashboardPage | Planned |
| `GET /dashboard/trends` | Time-series chart points | Static formula loop | Aggregated historical scores by timeframe/filters | ProductRepo | DashboardService | Time-series aggregation across 7d/30d/all, channel breakdown | DashboardPage | Planned |
| `GET /products` | Product catalog with filters | In-memory filtering without dynamic scoring | Dynamic scoring recalculation, multi-field ranking | ProductRepo | ProductService | TrendScore, Velocity, Growth, Demand, ViralPotential | ProductListPage | Planned |
| `GET /products/:id` | Product detail intelligence | Static product return | Real-time intelligence vector computation | ProductRepo | ProductService | Velocity index, platform divergence, related items | ProductDetailPage | Planned |
| `GET /products/compare` | Head-to-head comparison | Basic list lookup | Aligned historical curves & normalized matrix | ProductRepo | ComparisonService | Aligned daily trajectories, dimensional matrix | ProductComparisonPage | Planned |
| `GET /categories` | Category sector breakdowns | Static category objects | Derived dynamic metrics from product catalog | CategoryRepo, ProductRepo | CategoryService | Avg score, total volume, momentum, velocity label | CategoriesPage | Planned |
| `GET /platforms` | Platform channel pulse | Static platform list | Dynamic aggregation from signal events | PlatformRepo, ProductRepo | PlatformService | Total signals, active trends, velocity growth | PlatformsPage | Planned |
| `POST /reports/generate` | Executive report generation | Hardcoded string template | Multi-stage analytical synthesis from real data | ReportRepo, ProductRepo | ReportService | Category summary, anomaly extraction, top products | ReportGenerationPage | Planned |
| `GET /reports/:id/export` | Dossier export | Returns JSON for all formats | Real formatted CSV & JSON downloads | ReportRepo | ReportService | Structured CSV serialization, JSON export | ReportDetailPage, ReportsListPage | Planned |
| `GET /search` | Global entity search | Basic substring match | Ranked multi-entity relevance scoring | All Repos | SearchService | Relevance scoring, entity classification | CommandSearchModal, SearchPage | Planned |
| `POST /watchlist/:id` | Add product to watchlist | Flag update | Duplicate prevention, event notification trigger | WatchlistRepo, ProductRepo | WatchlistService | Watchlist count, state sync | WatchlistPage, ProductListPage | Planned |
| `GET /alerts` | System anomaly alerts | Static list | Dynamic alert generation based on real threshold triggers | AlertRepo, ProductRepo | AlertService | Spike detection (>200%), inventory drops | AlertsPage, Header | Planned |
| `POST /data-sources/:slug/connect` | Source ingestion toggle | In-memory status update | Connector initialization & simulated signal ingestion | DataSourceRepo | DataSourceService, IngestionPipeline | Telemetry health score, synced record count | DataSourcesPage | Planned |

## 2. Technical Architecture & Layering
1. **Domain Layer (`backend/app/domain/`)**:
   - `signals.py`: `PlatformSignal` normalized data model.
   - `scoring.py`: Velocity, Growth Rate, Momentum, and Composite Trend Score mathematical formulas.
   - `demand.py`: Demand Signal Strength classifier & confidence scoring.
   - `viral.py`: Viral Potential classifier based on cross-channel dispersion & velocity acceleration.
   - `aggregation.py`: Timeframe & category/platform aggregators.
2. **Ingestion & Connectors Layer (`backend/app/connectors/`)**:
   - `base.py`: `DataSourceConnector` abstract base class.
   - `mock_connectors.py`: Concrete mock connectors for TikTok, Daraz, Instagram, YouTube, Facebook.
3. **Services Layer (`backend/app/services/`)**:
   - `intelligence.py`: Comprehensive product intelligence engine.
   - `trend_service.py`: Multi-timeframe trend scoring.
   - `category_service.py`: Dynamic category analytics.
   - `platform_service.py`: Platform telemetry and pulse.
   - `dashboard_service.py`: Dashboard KPI and chart aggregations.
   - `search_service.py`: Catalog & cross-entity ranked search.
   - `watchlist_service.py`: Watchlist business rules and state synchronization.
   - `alert_service.py`: Real-time anomaly detection & alert lifecycle.
   - `notification_service.py`: Event-driven notification dispatch.
   - `report_service.py`: Multi-stage analytical report generation & CSV/JSON export.
   - `ai_insight_service.py`: Pluggable LLM insight synthesizer.
   - `ingestion_service.py`: Ingestion pipeline coordinator.
4. **API Endpoints Integration (`backend/app/api/v1/endpoints/`)**:
   - Refactor endpoints to delegate business logic to domain services.
5. **Testing & Regression Suite**:
   - Unit tests for all mathematical scoring formulas and engines.
   - Integration tests for all updated API endpoints.
   - Phase 1C regression validation (all 20 tests preserved + new tests).
