# Implementation Plan: Phase 2C — Live YouTube Data + Intelligence Agents

## 1. Architecture & Module Structure
```
backend/app/
├── core/
│   ├── config.py             # Extended YouTube params (YOUTUBE_MAX_RESULTS, YOUTUBE_REGION_CODE, ENVIRONMENT)
│   └── http_client.py        # Enhanced with QuotaExceeded error parsing
├── domain/
│   ├── signals.py            # Extended IngestionResult with is_live, matched/unmatched stats
│   ├── matching.py           # Enhanced ProductMatchingEngine with confidence threshold & unmatched classification
│   ├── classification.py     # CategoryClassificationService (rule & taxonomy classification agent)
│   ├── data_quality.py       # DataQualityService (schema, range, and metric validation agent)
│   └── prediction.py         # TrendPredictionService (deterministic trajectory & horizon forecasting)
├── connectors/
│   └── youtube_connector.py  # Production YouTubeDataConnector with live queries & parameter configuration
├── services/
│   └── ingestion_service.py  # Upgraded IngestionPipeline coordinating all quality, matching, and prediction agents
├── api/v1/endpoints/
│   ├── data_sources.py       # Endpoints for sync with live status & mode reporting
│   └── dev.py                # Development data reset endpoint (guarded by ENVIRONMENT=development)
frontend/src/
├── types/
│   └── index.ts              # Extended DataSource & IngestionResult types
├── services/
│   └── domainServices.ts     # Data source & dev reset service integration
└── pages/data_sources/
    └── DataSourcesPage.tsx   # Live vs Mock indicator, sync metrics breakdown
```

## 2. Ingestion & Agent Coordination Pipeline
1. `POST /api/v1/data-sources/youtube/sync` received.
2. Ingestion lock acquired for `youtube`.
3. `YouTubeDataConnector` queries YouTube Data API v3 (or controlled live payload).
4. `DataQualityService` validates fields, volumes, and ranges.
5. `ProductMatchingEngine` classifies records into `matched` vs `unmatched`.
6. `CategoryClassificationService` derives categories, subcategories, and confidence.
7. Deduplication engine checks `deduplication_key`.
8. `ProductRepository` updates signal counts, volume, and platform shares.
9. `ProductIntelligenceEngine` recomputes Trend Score, Velocity, Demand Index, and Viral Potential.
10. `TrendPredictionService` computes directional trajectory and 7d/30d predicted scores.
11. `AlertService` checks anomaly triggers and `NotificationService` dispatches events.
12. Returns comprehensive `IngestionResult`.

## 3. Testing Matrix
1. **Unit Tests**:
   - `test_data_quality.py`: Validation rules, negative volume rejection, timestamp parsing.
   - `test_category_classification.py`: Taxonomy mapping, subcategory derivation, confidence levels.
   - `test_trend_prediction.py`: Directional forecasting, momentum acceleration, 7d/30d horizon.
   - `test_youtube_connector.py`: Quota errors, 401 handling, search & statistics batching.
2. **Integration Tests**:
   - `test_ingestion_pipeline.py`: Single sync execution, unmatched record isolation, duplicate rejection.
   - `test_dev_reset.py`: Dev reset data endpoint.
3. **Regression Tests**:
   - All 47 existing backend tests passing.
   - Frontend `npm run lint` and `npm run build` passing.
