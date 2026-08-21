from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import statistics
from backend.app.core.config import settings
from backend.app.schemas.common import ResponseModel
from backend.app.repositories.in_memory import (
    InMemoryProductRepository, InMemoryDataSourceRepository,
    InMemoryAlertRepository, InMemoryNotificationRepository,
    InMemoryCategoryRepository, InMemoryPlatformRepository
)
from backend.app.api.deps import (
    get_product_repository, get_data_source_repository,
    get_alert_repository, get_notification_repository,
    get_category_repository, get_platform_repository,
    get_intelligence_engine
)
from backend.app.services.intelligence import ProductIntelligenceEngine
from backend.app.domain.backtesting import PredictionBacktester
from backend.app.domain.scoring import TrendScoringEngine
from backend.app.domain.prediction import TrendPredictionService
from backend.app.domain.classification import CategoryClassificationService

router = APIRouter()

def calculate_percentiles(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"p25": 0.0, "p50": 0.0, "p75": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}
    s = sorted(values)
    n = len(s)
    def pct(p: float) -> float:
        idx = int(round(p * (n - 1)))
        return round(s[min(max(idx, 0), n - 1)], 1)
    return {
        "p25": pct(0.25),
        "p50": pct(0.50),
        "p75": pct(0.75),
        "p90": pct(0.90),
        "p95": pct(0.95),
        "p99": pct(0.99)
    }

@router.post("/reset-data", response_model=ResponseModel[dict])
def reset_development_data(
    prod_repo: InMemoryProductRepository = Depends(get_product_repository),
    source_repo: InMemoryDataSourceRepository = Depends(get_data_source_repository),
    alert_repo: InMemoryAlertRepository = Depends(get_alert_repository),
    notif_repo: InMemoryNotificationRepository = Depends(get_notification_repository),
    cat_repo: InMemoryCategoryRepository = Depends(get_category_repository),
    plat_repo: InMemoryPlatformRepository = Depends(get_platform_repository)
):
    """
    Development-only endpoint to reset in-memory data structures to their initial seeded state.
    Forbidden in non-development environments.
    """
    if settings.ENVIRONMENT.lower() != "development":
        raise HTTPException(
            status_code=403,
            detail="Data reset endpoint is disabled outside development environment."
        )

    # Re-seed all repositories cleanly
    prod_repo._products.clear()
    prod_repo._seed_products()

    source_repo._sources.clear()
    source_repo.__init__()

    alert_repo._alerts.clear()
    alert_repo.__init__()

    notif_repo._notifications.clear()
    notif_repo.__init__()

    cat_repo._categories.clear()
    cat_repo.__init__()

    plat_repo._platforms.clear()
    plat_repo.__init__()

    return ResponseModel(
        success=True,
        message="In-memory development repositories successfully reset to baseline seed state.",
        data={"environment": settings.ENVIRONMENT, "reset": True}
    )

@router.get("/intelligence/summary", response_model=ResponseModel[dict])
def get_intelligence_summary(
    intelligence: ProductIntelligenceEngine = Depends(get_intelligence_engine),
    prod_repo: InMemoryProductRepository = Depends(get_product_repository),
    source_repo: InMemoryDataSourceRepository = Depends(get_data_source_repository),
    alert_repo: InMemoryAlertRepository = Depends(get_alert_repository)
):
    """
    Development diagnostics endpoint returning comprehensive statistical calibration,
    distribution percentiles, backtesting results, and version metadata.
    Forbidden outside development environment.
    """
    if settings.ENVIRONMENT.lower() != "development":
        raise HTTPException(
            status_code=403,
            detail="Intelligence diagnostics summary is disabled outside development environment."
        )

    products = intelligence.list_products()
    alerts = alert_repo.list()
    sources = source_repo.list()

    # Numerical distributions
    trend_scores = [p.trend_score for p in products]
    growth_rates = [p.growth_rate for p in products]
    volumes = [float(p.volume) for p in products]
    sentiment_scores = [p.sentiment_score for p in products]

    # Demand & Viral score extraction
    demand_scores = []
    viral_scores = []
    ready_predictions = 0

    for p in products:
        raw = p.raw_data or {}
        dem = raw.get("demand_detail", {})
        if "demand_score" in dem:
            demand_scores.append(dem["demand_score"])
        vir = raw.get("viral_detail", {})
        if "viral_score" in vir:
            viral_scores.append(vir["viral_score"])
        pred = raw.get("prediction", {})
        if pred.get("prediction_status") == "ready":
            ready_predictions += 1

    # Backtesting
    backtest_report = PredictionBacktester.run_catalog_backtest(products)

    # Ingestion sources & live tracking
    live_sources = [s for s in sources if getattr(s, "status", "") == "Connected" and getattr(s, "health_score", 0) >= 95]

    summary_data = {
        "environment": settings.ENVIRONMENT,
        "total_products": len(products),
        "total_alerts": len(alerts),
        "total_data_sources": len(sources),
        "metrics_summary": {
            "trend_score": {
                "mean": round(statistics.mean(trend_scores), 1) if trend_scores else 0.0,
                "median": round(statistics.median(trend_scores), 1) if trend_scores else 0.0,
                "percentiles": calculate_percentiles(trend_scores)
            },
            "growth_rate": {
                "mean": round(statistics.mean(growth_rates), 1) if growth_rates else 0.0,
                "median": round(statistics.median(growth_rates), 1) if growth_rates else 0.0,
                "percentiles": calculate_percentiles(growth_rates)
            },
            "volume": {
                "mean": round(statistics.mean(volumes), 0) if volumes else 0,
                "median": round(statistics.median(volumes), 0) if volumes else 0,
                "percentiles": calculate_percentiles(volumes)
            },
            "sentiment": {
                "mean": round(statistics.mean(sentiment_scores), 2) if sentiment_scores else 0.0,
                "median": round(statistics.median(sentiment_scores), 2) if sentiment_scores else 0.0
            },
            "demand_score": {
                "mean": round(statistics.mean(demand_scores), 1) if demand_scores else 0.0,
                "percentiles": calculate_percentiles(demand_scores)
            },
            "viral_score": {
                "mean": round(statistics.mean(viral_scores), 1) if viral_scores else 0.0,
                "percentiles": calculate_percentiles(viral_scores)
            }
        },
        "prediction_intelligence": {
            "prediction_coverage_count": ready_predictions,
            "prediction_coverage_percent": round((ready_predictions / max(len(products), 1)) * 100.0, 1),
            "backtest": backtest_report.to_dict()
        },
        "version_metadata": {
            "scoring_version": TrendScoringEngine.SCORING_VERSION,
            "prediction_version": TrendPredictionService.PREDICTION_VERSION,
            "classification_version": CategoryClassificationService.CLASSIFICATION_VERSION,
            "calibration_status": "CALIBRATED_PHASE_2D"
        }
    }

    return ResponseModel(
        success=True,
        message="Intelligence diagnostics summary computed successfully.",
        data=summary_data
    )
