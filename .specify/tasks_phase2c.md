# Phase 2C Tasks: Live YouTube Data + Intelligence Agents

## 1. Environment Configuration & Error Types
- [x] Task 1.1: Create root `.gitignore` ensuring `.env` and sensitive files are untracked.
- [x] Task 1.2: Create `backend/.env` with `YOUTUBE_API_KEY`, `ENVIRONMENT=development`, `YOUTUBE_MAX_RESULTS=50`, `YOUTUBE_REGION_CODE=US`, `YOUTUBE_LANGUAGE=en`.
- [x] Task 1.3: Update `backend/.env.example` with safe blank placeholders.
- [x] Task 1.4: Update `backend/app/core/config.py` with validated environment variables.
- [x] Task 1.5: Enhance `backend/app/core/http_client.py` with `QuotaExceededException` and `AuthenticationException`.

## 2. Intelligence Agents Layer
- [x] Task 2.1: Implement `DataQualityService` (`backend/app/domain/data_quality.py`).
- [x] Task 2.2: Implement `CategoryClassificationService` (`backend/app/domain/classification.py`).
- [x] Task 2.3: Implement `TrendPredictionService` (`backend/app/domain/prediction.py`).
- [x] Task 2.4: Update `ProductMatchingEngine` (`backend/app/domain/matching.py`) for detailed match types and confidence.
- [x] Task 2.5: Extend `IngestionResult` model (`backend/app/domain/signals.py`).

## 3. Connectors & Ingestion Pipeline
- [x] Task 3.1: Upgrade `YouTubeDataConnector` (`backend/app/connectors/youtube_connector.py`) with configurable batch queries.
- [x] Task 3.2: Enhance `IngestionPipeline` (`backend/app/services/ingestion_service.py`) with full agent coordination pipeline.
- [x] Task 3.3: Implement `POST /api/v1/dev/reset-data` endpoint (`backend/app/api/v1/endpoints/dev.py`).
- [x] Task 3.4: Add `GET /api/v1/data-sources/config/status` endpoint (`backend/app/api/v1/endpoints/data_sources.py`).
- [x] Task 3.5: Mount dev router in `backend/app/api/v1/router.py`.

## 4. Frontend UI & Domain Services
- [x] Task 4.1: Update frontend types (`frontend/src/types/index.ts`) for `IngestionResult` and `DataSourceConfigStatus`.
- [x] Task 4.2: Update frontend domain services (`frontend/src/services/domainServices.ts`).
- [x] Task 4.3: Update `DataSourcesPage.tsx` with Live vs Mock badge, Dev Reset button, and telemetry feedback.

## 5. Verification & Testing
- [x] Task 5.1: Create unit test suite `test_data_quality.py`.
- [x] Task 5.2: Create unit test suite `test_category_classification.py`.
- [x] Task 5.3: Create unit test suite `test_trend_prediction.py`.
- [x] Task 5.4: Create unit test suite `test_dev_reset.py`.
- [x] Task 5.5: Run full pytest suite across backend (58 passed, 1 skipped).
- [x] Task 5.6: Run frontend `npm run lint` (0 errors) and `npm run build` (PASS).
- [x] Task 5.7: Synchronize Walkthrough and Deliver Final Phase 2C Report.
