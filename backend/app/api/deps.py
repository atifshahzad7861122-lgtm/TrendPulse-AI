from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from backend.app.core.config import settings
from backend.app.models.domain import User
from backend.app.repositories.base import (
    UserRepository, WorkspaceRepository, AuthPersistenceRepository, SubscriptionRepository, CreditRepository,
    ProductRepository, CategoryRepository, PlatformRepository, WatchlistRepository, AlertRepository,
    NotificationRepository, ReportRepository, DataSourceRepository, SettingsRepository
)
from backend.app.repositories.in_memory import (
    user_repo, workspace_repo, auth_persistence_repo, subscription_repo, credit_repo,
    product_repo, category_repo, platform_repo, watchlist_repo, alert_repo, notification_repo,
    report_repo, data_source_repo, settings_repo
)
from backend.app.repositories.postgres import (
    PostgresUserRepository, PostgresWorkspaceRepository, PostgresAuthPersistenceRepository,
    PostgresSubscriptionRepository, PostgresCreditRepository, PostgresProductRepository,
    PostgresCategoryRepository, PostgresPlatformRepository, PostgresWatchlistRepository,
    PostgresAlertRepository, PostgresNotificationRepository, PostgresReportRepository,
    PostgresDataSourceRepository, PostgresSettingsRepository
)
from backend.app.services.auth_service import AuthService
from backend.app.services.credit_service import CreditService
from backend.app.services.subscription_service import SubscriptionService
from backend.app.services.intelligence import ProductIntelligenceEngine
from backend.app.services.category_service import CategoryService
from backend.app.services.platform_service import PlatformService
from backend.app.services.dashboard_service import DashboardService
from backend.app.services.search_service import SearchService
from backend.app.services.watchlist_service import WatchlistService
from backend.app.services.alert_service import AlertService
from backend.app.services.notification_service import NotificationService
from backend.app.services.report_service import ReportService
from backend.app.services.data_sources_service import DataSourceService
from backend.app.services.ingestion_service import IngestionPipeline

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

def _is_postgres_backend() -> bool:
    mode = getattr(settings, "DATA_BACKEND", "in_memory").lower()
    if mode == "postgres":
        if not getattr(settings, "DATABASE_URL", None):
            raise RuntimeError(
                "DATA_BACKEND is set to 'postgres' but DATABASE_URL is not configured in environment."
            )
        return True
    return False

def get_user_repository() -> UserRepository:
    if _is_postgres_backend():
        return PostgresUserRepository()
    return user_repo

def get_workspace_repository() -> WorkspaceRepository:
    if _is_postgres_backend():
        return PostgresWorkspaceRepository()
    return workspace_repo

def get_auth_persistence_repository() -> AuthPersistenceRepository:
    if _is_postgres_backend():
        return PostgresAuthPersistenceRepository()
    return auth_persistence_repo

def get_subscription_repository() -> SubscriptionRepository:
    if _is_postgres_backend():
        return PostgresSubscriptionRepository()
    return subscription_repo

def get_credit_repository() -> CreditRepository:
    if _is_postgres_backend():
        return PostgresCreditRepository()
    return credit_repo

def get_product_repository() -> ProductRepository:
    if _is_postgres_backend():
        return PostgresProductRepository()
    return product_repo

def get_category_repository() -> CategoryRepository:
    if _is_postgres_backend():
        return PostgresCategoryRepository()
    return category_repo

def get_platform_repository() -> PlatformRepository:
    if _is_postgres_backend():
        return PostgresPlatformRepository()
    return platform_repo

def get_watchlist_repository() -> WatchlistRepository:
    if _is_postgres_backend():
        return PostgresWatchlistRepository()
    return watchlist_repo

def get_alert_repository() -> AlertRepository:
    if _is_postgres_backend():
        return PostgresAlertRepository()
    return alert_repo

def get_notification_repository() -> NotificationRepository:
    if _is_postgres_backend():
        return PostgresNotificationRepository()
    return notification_repo

def get_report_repository() -> ReportRepository:
    if _is_postgres_backend():
        return PostgresReportRepository()
    return report_repo

def get_data_source_repository() -> DataSourceRepository:
    if _is_postgres_backend():
        return PostgresDataSourceRepository()
    return data_source_repo

def get_settings_repository() -> SettingsRepository:
    if _is_postgres_backend():
        return PostgresSettingsRepository()
    return settings_repo

# Service Providers
def get_credit_service(
    credits: CreditRepository = Depends(get_credit_repository)
) -> CreditService:
    return CreditService(credits)

def get_subscription_service(
    subs: SubscriptionRepository = Depends(get_subscription_repository),
    credit_service: CreditService = Depends(get_credit_service)
) -> SubscriptionService:
    return SubscriptionService(subs, credit_service)

def get_auth_service(
    users: UserRepository = Depends(get_user_repository),
    workspaces: WorkspaceRepository = Depends(get_workspace_repository),
    auth_persistence: AuthPersistenceRepository = Depends(get_auth_persistence_repository),
    settings_repo: SettingsRepository = Depends(get_settings_repository),
    subscriptions: SubscriptionRepository = Depends(get_subscription_repository),
    credits: CreditRepository = Depends(get_credit_repository)
) -> AuthService:
    return AuthService(users, workspaces, auth_persistence, settings_repo, subscriptions, credits)

def get_product_intelligence_engine(
    products: ProductRepository = Depends(get_product_repository)
) -> ProductIntelligenceEngine:
    return ProductIntelligenceEngine(products)

get_intelligence_engine = get_product_intelligence_engine

def get_category_service(
    categories: CategoryRepository = Depends(get_category_repository),
    products: ProductRepository = Depends(get_product_repository)
) -> CategoryService:
    return CategoryService(categories, products)

def get_platform_service(
    platforms: PlatformRepository = Depends(get_platform_repository),
    products: ProductRepository = Depends(get_product_repository)
) -> PlatformService:
    return PlatformService(platforms, products)

def get_dashboard_service(
    products: ProductRepository = Depends(get_product_repository),
    alerts: AlertRepository = Depends(get_alert_repository),
    platforms: PlatformRepository = Depends(get_platform_repository)
) -> DashboardService:
    return DashboardService(products, alerts, platforms)

def get_search_service(
    products: ProductRepository = Depends(get_product_repository),
    categories: CategoryRepository = Depends(get_category_repository),
    platforms: PlatformRepository = Depends(get_platform_repository),
    reports: ReportRepository = Depends(get_report_repository),
    alerts: AlertRepository = Depends(get_alert_repository)
) -> SearchService:
    return SearchService(products, categories, platforms, reports, alerts)

def get_watchlist_service(
    watchlist: WatchlistRepository = Depends(get_watchlist_repository),
    products: ProductRepository = Depends(get_product_repository)
) -> WatchlistService:
    return WatchlistService(watchlist, products)

def get_alert_service(
    alerts: AlertRepository = Depends(get_alert_repository),
    products: ProductRepository = Depends(get_product_repository)
) -> AlertService:
    return AlertService(alerts, products)

def get_notification_service(
    notifications: NotificationRepository = Depends(get_notification_repository)
) -> NotificationService:
    return NotificationService(notifications)

def get_report_service(
    reports: ReportRepository = Depends(get_report_repository),
    products: ProductRepository = Depends(get_product_repository)
) -> ReportService:
    return ReportService(reports, products)

def get_data_source_service(
    sources: DataSourceRepository = Depends(get_data_source_repository)
) -> DataSourceService:
    return DataSourceService(sources)

def get_ingestion_pipeline(
    products: ProductRepository = Depends(get_product_repository),
    data_sources: DataSourceRepository = Depends(get_data_source_repository),
    intelligence: ProductIntelligenceEngine = Depends(get_product_intelligence_engine),
    alerts: AlertService = Depends(get_alert_service),
    notifications: NotificationService = Depends(get_notification_service)
) -> IngestionPipeline:
    return IngestionPipeline(
        product_repo=products,
        datasource_repo=data_sources,
        intelligence_engine=intelligence,
        alert_service=alerts,
        notification_service=notifications
    )

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    users: UserRepository = Depends(get_user_repository),
    auth_persistence: AuthPersistenceRepository = Depends(get_auth_persistence_repository)
) -> User:
    if not token:
        demo = users.get_by_id("usr_demo_101")
        if demo:
            return demo
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = users.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")
    return user
