# Phase 2D Specification: Real Data Quality + Intelligence Calibration + Prediction Validation

## 1. Context & Objectives
Phase 2D focuses on auditing, calibrating, and validating the intelligence generated from real and normalized data in TrendPulse AI. It elevates mathematical accuracy, explainability, backtesting rigor, and cross-domain consistency across all intelligence engines without introducing unauthorized external frameworks, databases, or UI redesigns.

## 2. Core Architectural Specifications

### 2.1 Live vs Mock Data Isolation & Signal Schema
- Extend `PlatformSignal` with:
  - `mode: str = "mock"` ("live" | "mock")
  - `data_quality_score: float = 100.0` (0 - 100)
  - `quality_flags: List[str]`
  - `like_rate: float`
  - `comment_rate: float`
- Update connectors (`YouTubeDataConnector`, mock connectors) to explicitly tag `mode="live"` or `mode="mock"`.

### 2.2 Data Quality Scoring Agent
- `DataQualityService.evaluate_quality(signal: PlatformSignal) -> Tuple[float, List[str], List[str]]`:
  - Formula:
    - Baseline: 100.0
    - Missing channel/title: -40.0
    - Negative counters: -50.0
    - Impossible engagement rate (> 0.50): -20.0
    - Spam/Clickbait detected: -15.0
    - Unrealistic ratio anomalies: -10.0
  - Rejection threshold: `score < 40.0` or invalid schema.

### 2.3 Hierarchical Category Classification Agent
- Taxonomy Hierarchy:
  - `Category` -> `Subcategory` -> `Product Type`
- Fallback:
  - If confidence < 0.50: Category = "Unclassified", Subcategory = "Needs Review", Product Type = "General Item".

### 2.4 Product Matching Engine with Calibrated Confidence
- Return match types: `matched` (confidence $\ge 0.75$), `ambiguous` ($0.50 \le \text{confidence} < 0.75$), `unmatched` ($\text{confidence} < 0.50$).
- Match factors: Canonical name, Token overlap, Brand aliases, Category domain keywords, Tag matches.

### 2.5 Explainable Trend Scoring Engine
- Output model: `TrendScoreDetail` containing:
  - `trend_score: float` (10.0 - 99.5)
  - `growth_component: float`
  - `velocity_component: float`
  - `momentum_component: float`
  - `volume_component: float`
  - `engagement_component: float`
  - `dispersion_component: float`
  - `top_contributors: List[str]`
  - `scoring_version: str = "2.4.0"`

### 2.6 Calibrated Demand & Viral Potential Engines
- `DemandSignalEngine`:
  - Returns `(label, score, confidence, contributors)`
  - Scaled across volume, engagement rate, growth rate, and sentiment.
- `ViralPotentialEngine`:
  - Returns `(label, score, confidence, contributors)`
  - Scaled across growth acceleration, velocity label, TikTok/IG presence, and cross-channel dispersion.

### 2.7 Prediction Validation & Deterministic Backtesting
- `TrendPredictionService`:
  - If observation count < 3 or historical span < 7 days: return `prediction_status="insufficient_history"`, `predicted_score_7d=None`, `predicted_score_30d=None`, `confidence=0`.
  - Otherwise calculate `predicted_score_7d`, `predicted_score_30d`, `direction`, `confidence` ($20 - 95\%$), `prediction_status="ready"`.
- `PredictionBacktester`:
  - Deterministic evaluation function running sliding window backtests on historical signals.
  - Computes `MAE`, `RMSE`, `Directional Accuracy (%)`.

### 2.8 Alert Calibration & Explainability
- Alert trigger rules:
  - Spike: growth $\ge 300\%$ -> `Critical`
  - Warning: growth $\ge 180\%$ or velocity acceleration -> `Warning`
  - Info: multi-platform expansion or competitor entry -> `Info`
- Return `trigger`, `threshold`, `actual_value`, `severity`.

### 2.9 Deterministic Replay & Versioning
- Ingestion Replay test utility: given dataset $D$, $Ingest(D) = Ingest(D)$ producing identical product metrics.
- Version metadata exposed across intelligence domain entities.

### 2.10 Development Intelligence Diagnostics Endpoint
- `GET /api/v1/dev/intelligence/summary`:
  - Enabled only when `ENVIRONMENT=development`.
  - Returns live vs mock counts, match breakdown, score distributions, prediction coverage, and backtesting metrics.
