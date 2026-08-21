# Specification: Phase 2B — Real Data Connector + Production Ingestion Pipeline

## 1. Overview & Objectives
Phase 2B implements a production-grade external data ingestion pipeline for TrendPulse AI, integrating the first live external data source (**YouTube Data API v3**) while preserving the abstract `DataSourceConnector` contract.

The pipeline performs end-to-end data flow:
$$\text{External REST API} \longrightarrow \text{Raw Validation} \longrightarrow \text{Normalization (\text{PlatformSignal})} \longrightarrow \text{Deduplication} \longrightarrow \text{Product Matching} \longrightarrow \text{Repository Storage} \longrightarrow \text{Intelligence Recalculation} \longrightarrow \text{Dashboard/Alerts/Reports}$$

## 2. Selected Production Source: YouTube Data API v3
- **Rationale**:
  - Direct support for video view counts, likes, comments, published timestamps, search queries for trending consumer products, and high-velocity commerce signals.
  - Official, reliable Google REST endpoints with deterministic response formats.
  - Standard API Key authentication (`YOUTUBE_API_KEY`).
  - Clear rate limit handling (HTTP 429 and `quotaExceeded`).
  - Native cursor pagination (`nextPageToken`).
- **Telemetry Mapping into `PlatformSignal`**:
  - `volume` $\leftarrow$ `statistics.viewCount`
  - `views_count` $\leftarrow$ `statistics.viewCount`
  - `likes_count` $\leftarrow$ `statistics.likeCount`
  - `comments_count` $\leftarrow$ `statistics.commentCount`
  - `engagement_rate` $\leftarrow (\text{likes} + \text{comments}) / \max(\text{views}, 1)$
  - `sentiment_score` $\leftarrow$ Computed from positive/negative keyword density in video snippet and title.
  - `timestamp` $\leftarrow$ `publishedAt` converted to strict UTC `datetime`.

## 3. Production Ingestion Architecture & Components
1. **HTTP Client & Resilience**:
   - `backend/app/core/http_client.py`: Async-ready HTTP client with:
     - Configurable timeouts (`DATA_SOURCE_TIMEOUT_SECONDS`, default 15s).
     - Exponential backoff retry policy for transient errors (408, 429, 500, 502, 503, 504) up to 3 attempts.
     - Rate-limit 429 detection capturing provider response and `Retry-After`.
     - Zero credential leakage in logs or exceptions.
2. **Production Connector (`backend/app/connectors/youtube_connector.py`)**:
   - Implements `DataSourceConnector` ABC.
   - Methods: `fetch_signals(limit, query)`, `test_connection()`, `normalize_raw_video()`.
   - Cursor-based pagination with max page safety limits.
   - Seamless fallback when `YOUTUBE_API_KEY` is not provided (allowing full offline testing in CI).
3. **Product Matching & Normalization Engine (`backend/app/domain/matching.py`)**:
   - Matches external signal content (titles, tags, descriptions) to canonical products in the catalog.
   - Prevents accidental merging of distinct products.
4. **Deduplication Strategy**:
   - Composite unique key: `f"{platform}:{product_id}:{external_item_id}"` or `f"{platform}:{product_id}:{published_date}"`.
   - Prevents duplicate volume inflation on repeated syncs.
5. **Thread-Safe Ingestion Pipeline & Concurrency Control (`backend/app/services/ingestion_service.py`)**:
   - Ingestion cycle execution with per-source sync locking to prevent duplicate concurrent runs.
   - Returns structured `IngestionResult` (`source`, `started_at`, `completed_at`, `records_received`, `records_normalized`, `records_inserted`, `records_updated`, `records_skipped`, `records_failed`, `status`, `errors`).
   - Post-ingestion recalculation triggers: updates product signals, recalculates trend scores, recalculates category and platform metrics, evaluates alert triggers, and dispatches notifications.
6. **API Endpoints**:
   - `POST /api/v1/data-sources/{slug}/sync`: On-demand source sync returning structured telemetry.
   - `POST /api/v1/data-sources/sync-all`: Executes all enabled connectors.
   - `GET /api/v1/data-sources`: Returns live telemetry (records synced, health score, last sync time).
7. **Frontend Data Sources UI Enhancement**:
   - Add on-demand "Sync Now" action buttons and "Sync All Sources" trigger.
   - Visual feedback displaying structured ingestion toast and record counts.

## 4. Strict Constraints & Deferrals
- **PostgreSQL**: STRICTLY DEFERRED. In-memory thread-safe repositories are maintained behind abstract repository interfaces.
- **Production AI (Qwen)**: STRICTLY DEFERRED. Deterministic `AIInsightService` summaries remain in place.
- **Mock Connectors**: TikTok, Daraz, Instagram, and Facebook mock connectors remain fully functional behind the same `DataSourceConnector` interface.
