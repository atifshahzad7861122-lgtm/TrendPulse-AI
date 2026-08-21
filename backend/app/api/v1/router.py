from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    auth, workspace, dashboard, products, categories, platforms,
    watchlist, alerts, notifications, reports, data_sources, search, settings, dev, health,
    credits, subscription
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(platforms.router, prefix="/platforms", tags=["platforms"])
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
