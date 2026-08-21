# Implementation Plan: Phase 2B — Real Data Connector + Production Ingestion Pipeline

## 1. Architectural Architecture & File Changes
```
backend/app/
├── core/
│   ├── config.py           # Add YOUTUBE_API_KEY, DATA_SOURCE_TIMEOUT, DATA_SOURCE_ENABLED
│   └── http_client.py      # Resilient HTTP client with retries, timeouts, 429 rate limit detection
├── domain/
│   ├── signals.py          # PlatformSignal, SignalBatch, IngestionResult schema
│   └── matching.py         # ProductMatchingEngine (external data -> canonical product catalog)
├── connectors/
│   ├── base.py             # DataSourceConnector interface
│   ├── mock_connectors.py  # Mock connectors for TikTok, Daraz, Instagram, Facebook
│   └── youtube_connector.py # Production YouTubeDataConnector with fallback & pagination
├── services/
│   ├── ingestion_service.py # IngestionPipeline with concurrency lock & post-sync recalculations
│   └── data_sources_service.py # DataSourceService lifecycle management
├── api/v1/endpoints/
│   └── data_sources.py     # Endpoints for sync, sync-all, connect, disconnect
frontend/src/
├── services/
│   └── domainServices.ts   # Add sync and syncAll endpoints
├── types/
│   └── index.ts            # Extend DataSource and IngestionResult types if needed
└── pages/data_sources/
    └── DataSourcesPage.tsx # Add Sync Now and Sync All actions with live status feedback
```

## 2. Ingestion & Recalculation Flow
1. User or automated schedule triggers `POST /api/v1/data-sources/youtube/sync`.
2. `IngestionPipeline` acquires per-source lock to prevent concurrent collisions.
3. `YouTubeDataConnector` fetches external REST data with configured timeouts & retries.
4. Raw items are validated and normalized into `PlatformSignal`.
5. Signals are deduplicated using composite keys against in-memory repository.
6. Signals are matched to products via `ProductMatchingEngine`.
7. Repository updates product signal count, volume, and platform shares.
8. `ProductIntelligenceEngine` recalculates trend scores, velocity labels, and demand indices.
9. `AggregationEngine` updates category and platform metrics dynamically.
10. `AlertService` evaluates product thresholds (e.g. growth > 200%) and generates structured alerts.
11. Returns structured `IngestionResult` to the client.

## 3. Testing & Verification Matrix
1. **Unit Tests (`test_youtube_connector.py` & `test_http_client.py`)**:
   - Resilient HTTP client retry logic on 500, 502, 503, 504.
   - Rate limit 429 detection and timeout handling.
   - Raw YouTube payload normalization into `PlatformSignal`.
   - Cursor-based pagination and max page limit adherence.
   - Deterministic deduplication on repeated sync runs.
2. **Integration Tests (`test_ingestion_pipeline.py`)**:
   - `POST /api/v1/data-sources/youtube/sync` structured output validation.
   - Dynamic update of Product volume, Trend Score, Category, and Platform metrics post-sync.
   - Anomaly alert generation triggered by ingested signals.
3. **Regression Tests**:
   - Pytest suite (Phase 1C + Phase 2A tests) all passing.
   - Frontend `npm run lint` and `npm run build` passing.
