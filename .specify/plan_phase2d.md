# Phase 2D Plan: Real Data Quality + Intelligence Calibration + Prediction Validation

## 1. Objectives & Approach
1. Enhance signal modeling with explicit `mode` ("live" | "mock"), normalized rates, and `data_quality_score`.
2. Upgrade `DataQualityService` with multi-factor quality scoring.
3. Enhance `CategoryClassificationService` with hierarchical taxonomy (`Category` -> `Subcategory` -> `Product Type`) and confidence scoring.
4. Calibrate `ProductMatchingEngine` with robust confidence thresholds and ambiguous handling.
5. Upgrade `TrendScoringEngine`, `DemandSignalEngine`, and `ViralPotentialEngine` to return explainable breakdowns and contributor lists.
6. Upgrade `TrendPredictionService` with `insufficient_history` safeguards and implement `PredictionBacktester` for MAE/RMSE/Directional accuracy evaluation.
7. Enhance `AlertService` with explainable trigger telemetry (`trigger`, `threshold`, `actual_value`).
8. Add deterministic snapshot & replay capabilities.
9. Implement `GET /api/v1/dev/intelligence/summary` endpoint for development diagnostics.
10. Update frontend interfaces to surface intelligence explainability, confidence, and prediction status cleanly.
11. Write comprehensive unit and integration tests.

## 2. Component Architecture
- **Signals & Connectors**: `backend/app/domain/signals.py`, `backend/app/connectors/youtube_connector.py`, mock connectors.
- **Domain Intelligence**:
  - `backend/app/domain/data_quality.py`
  - `backend/app/domain/classification.py`
  - `backend/app/domain/matching.py`
  - `backend/app/domain/scoring.py`
  - `backend/app/domain/demand.py`
  - `backend/app/domain/viral.py`
  - `backend/app/domain/prediction.py`
  - `backend/app/domain/backtesting.py`
- **Services & Repositories**:
  - `backend/app/services/ingestion_service.py`
  - `backend/app/services/alert_service.py`
  - `backend/app/services/product_service.py`
  - `backend/app/services/dashboard_service.py`
- **API Endpoints**:
  - `backend/app/api/v1/endpoints/dev.py`
  - `backend/app/api/v1/endpoints/products.py`
- **Frontend Integration**:
  - `frontend/src/types/index.ts`
  - `frontend/src/pages/products/ProductDetailPage.tsx`
  - `frontend/src/pages/data_sources/DataSourcesPage.tsx`
- **Verification Suites**:
  - `backend/tests/test_data_quality_calibrated.py`
  - `backend/tests/test_category_hierarchy.py`
  - `backend/tests/test_trend_scoring_explainability.py`
  - `backend/tests/test_prediction_backtesting.py`
  - `backend/tests/test_alert_calibration.py`
  - `backend/tests/test_replay_determinism.py`
  - `backend/tests/test_intelligence_summary_endpoint.py`
