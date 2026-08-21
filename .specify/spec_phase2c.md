# Specification: Phase 2C — Live YouTube Data + Intelligence Agents

## 1. Overview & Objectives
Phase 2C completes the transition from offline fallback telemetry to live **YouTube Data API v3** ingestion coupled with specialized, deterministic **Intelligence Services & Agents**:
- `YouTubeDataCollector` (Live API v3 Query, Quota, and Error handling).
- `DataQualityService` (Validation, Anomaly Rejection, Schema Integrity).
- `ProductMatchingEngine` (High-confidence entity resolution with UNMATCHED segregation).
- `CategoryClassificationService` (Rule-based taxonomy mapping & confidence scoring).
- `TrendPredictionService` (Deterministic statistical trajectory forecasting: direction, confidence, 7d/30d predicted score).
- `ProductIntelligenceEngine` (Trend score, Demand score, Viral potential recalculation).
- `AlertService` & `NotificationService` (Real threshold-triggered event dispatching).
- Downstream propagation across Dashboard, Products, Categories, Platforms, and Reports.

## 2. YouTube API Configuration & Safety
- Environment variables:
  - `YOUTUBE_API_KEY`: Loaded from `.env`, never printed in logs, never returned by APIs, never bundled in React.
  - `YOUTUBE_MAX_RESULTS`: Default `50`.
  - `YOUTUBE_REGION_CODE`: Default `US`.
  - `YOUTUBE_LANGUAGE`: Default `en`.
- Configuration Status API:
  - Safe boolean/mode flag: `is_live_configured: bool`, `live_mode: "LIVE" | "MOCK"`.
- Error Differentiation:
  - Returns `401 Unauthorized` / `403 QuotaExceeded` / `429 RateLimit` explicitly when live sync fails, rather than silently masquerading as success.

## 3. Intelligence Agent Layer
1. **Data Quality Agent (`DataQualityService`)**:
   - Inspects volume $\ge 0$, engagement rate within $[0.0, 1.0]$, strict ISO 8601 UTC timestamp, and non-empty product/channel name.
   - Generates structured quality report (`records_valid`, `records_invalid`, `warnings`, `rejection_reasons`).
2. **Category Classification Agent (`CategoryClassificationService`)**:
   - Maps product/video signals to canonical taxonomies:
     - *Beauty & Personal Care* (Skincare, Cosmetics)
     - *Sports & Outdoor* (Athletic Gear, Hydration)
     - *Consumer Electronics* (Mobile Accessories, Audio)
     - *Home & Living* (Beverage Prep, Ergonomics)
     - *Fashion & Apparel* (Activewear, Streetwear)
   - Outputs: `category`, `subcategory`, `confidence` (0.0–1.0), `reason`.
3. **Product Matching Agent (`ProductMatchingEngine`)**:
   - Evaluates token overlap, title keywords, tag phrases.
   - Categorizes outcomes into: `matched`, `unmatched`, `ambiguous`.
   - Protects catalog integrity by marking low-confidence items as `UNMATCHED`.
4. **Trend Prediction Agent (`TrendPredictionService`)**:
   - Computes trajectory direction (`rising`, `stable`, `declining`).
   - Forecasts 7d and 30d projected trend scores using momentum acceleration ($\Delta V / \Delta t$) and exponential smoothing.
   - Generates statistical confidence index (0–100).

## 4. Ingestion Result & State Management
- Ingestion telemetry schema:
  - `source`: "youtube"
  - `is_live`: bool
  - `status`: "Success" | "RateLimited" | "QuotaExceeded" | "Failed"
  - `started_at`, `completed_at`, `duration_seconds`
  - `records_received`, `records_normalized`, `records_matched`, `records_unmatched`, `records_inserted`, `records_updated`, `records_skipped`, `records_failed`
  - `alerts_created`, `notifications_created`
  - `errors`: List[str]

## 5. Development Data Reset Endpoint
- `POST /api/v1/dev/reset-data`:
  - Guarded strictly by `ENVIRONMENT=development`.
  - Re-seeds in-memory repositories to initial baseline for clean testing and reproducibility.

## 6. Strict Boundary Constraints
- **PostgreSQL**: STRICTLY DEFERRED. In-memory thread-safe repositories maintained behind clean repository interfaces.
- **Production AI (Qwen)**: STRICTLY DEFERRED. Deterministic `AIInsightService` maintained.
- **Mock Connectors**: TikTok, Daraz, Instagram, and Facebook mock connectors preserved.
