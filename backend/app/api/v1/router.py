from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    auth, workspace, dashboard, products, categories, platforms,
    watchlist, alerts, notifications, reports, data_sources, search, settings, dev, health,
    credits, subscription, daraz, signals, shopify, intelligence, llm, agents, public_data_quality,
    categorization, taxonomy, entity_matching, agent_trend_detection, agent_anomaly_detection,
    agent_recommendations, agent_market_opportunities, scraper, marketplace_search,
    market_intelligence
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(categorization.router, prefix="/agents/categorization", tags=["categorization-agent"])
api_router.include_router(entity_matching.router, prefix="/agents/entity-matching", tags=["entity-matching-agent"])
api_router.include_router(agent_trend_detection.router, tags=["trend-detection-agent"])
api_router.include_router(agent_anomaly_detection.router, tags=["anomaly-detection-agent"])
api_router.include_router(agent_recommendations.router, tags=["recommendations-agent"])
api_router.include_router(agent_market_opportunities.router, tags=["market-opportunity-agent"])
api_router.include_router(taxonomy.router, prefix="/taxonomy", tags=["taxonomy"])
api_router.include_router(public_data_quality.router, prefix="/public/data-quality", tags=["public-data-quality"])


api_router.include_router(llm.router, prefix="/llm", tags=["llm"])
api_router.include_router(intelligence.router, prefix="/products/intelligence", tags=["intelligence"])
api_router.include_router(market_intelligence.router, prefix="/intelligence", tags=["market-intelligence"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(scraper.router, prefix="/scraper", tags=["scraper"])
api_router.include_router(marketplace_search.router, prefix="/marketplace-search", tags=["marketplace-search"])


api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(platforms.router, prefix="/platforms", tags=["platforms"])
api_router.include_router(daraz.router, prefix="/platforms/daraz", tags=["daraz"])
api_router.include_router(shopify.router, prefix="/platforms/shopify", tags=["shopify"])
api_router.include_router(signals.router, prefix="/signals", tags=["signals"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(data_sources.router, prefix="/data-sources", tags=["data-sources"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(credits.router, prefix="/credits", tags=["credits"])
api_router.include_router(subscription.router, prefix="/subscription", tags=["subscription"])
api_router.include_router(dev.router, prefix="/dev", tags=["dev"])



