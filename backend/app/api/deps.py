from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from backend.app.core.config import settings
from backend.app.models.domain import User
from backend.app.repositories.base import (
    UserRepository, WorkspaceRepository, AuthPersistenceRepository, SubscriptionRepository, CreditRepository,
    ProductRepository, CategoryRepository, PlatformRepository, WatchlistRepository, AlertRepository,
    NotificationRepository, ReportRepository, DataSourceRepository, SettingsRepository,
    MarketplaceProductRepository, ShopifyRepository, UnifiedProductRepository, LLMUsageRepository,
    DataQualityRepository, TaxonomyRepository, ScraperRepository, MarketIntelligenceRepository
)
from backend.app.repositories.in_memory import (
    user_repo, workspace_repo, auth_persistence_repo, subscription_repo, credit_repo,
    product_repo, category_repo, platform_repo, watchlist_repo, alert_repo, notification_repo,
    report_repo, data_source_repo, settings_repo, marketplace_product_repo, shopify_repo,
    unified_product_repo, llm_usage_repo, data_quality_repo, taxonomy_repo, scraper_repo,
    market_intelligence_repo
)
from backend.app.repositories.postgres import (
    PostgresUserRepository, PostgresWorkspaceRepository, PostgresAuthPersistenceRepository,
    PostgresSubscriptionRepository, PostgresCreditRepository, PostgresProductRepository,
    PostgresCategoryRepository, PostgresPlatformRepository, PostgresWatchlistRepository,
    PostgresAlertRepository, PostgresNotificationRepository, PostgresReportRepository,
    PostgresDataSourceRepository, PostgresSettingsRepository, PostgresMarketplaceProductRepository,
    PostgresShopifyRepository, PostgresUnifiedProductRepository, PostgresLLMUsageRepository,
    PostgresDataQualityRepository, PostgresTaxonomyRepository, PostgresScraperRepository,
    PostgresMarketIntelligenceRepository
)
from backend.app.services.agents.data_quality import DataQualityAgent
from backend.app.services.agents.categorization import ProductCategorizationAgent
from backend.app.services.agents.entity_matching import ProductEntityMatchingAgent


from backend.app.services.llm.service import LLMService
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
from backend.app.services.shopify.service import ShopifyService
from backend.app.services.unified_intelligence_service import UnifiedProductIntelligenceService

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

from backend.app.db.session import get_sync_session

def get_user_repository() -> UserRepository:
    if _is_postgres_backend():
        return PostgresUserRepository(session=get_sync_session())
    return user_repo

def get_workspace_repository() -> WorkspaceRepository:
    if _is_postgres_backend():
        return PostgresWorkspaceRepository(session=get_sync_session())
    return workspace_repo

def get_auth_persistence_repository() -> AuthPersistenceRepository:
    if _is_postgres_backend():
        return PostgresAuthPersistenceRepository(session=get_sync_session())
    return auth_persistence_repo

def get_subscription_repository() -> SubscriptionRepository:
    if _is_postgres_backend():
        return PostgresSubscriptionRepository(session=get_sync_session())
    return subscription_repo

def get_credit_repository() -> CreditRepository:
    if _is_postgres_backend():
        return PostgresCreditRepository(session=get_sync_session())
    return credit_repo

def get_product_repository() -> ProductRepository:
    if _is_postgres_backend():
        return PostgresProductRepository(session=get_sync_session())
    return product_repo

def get_category_repository() -> CategoryRepository:
    if _is_postgres_backend():
        return PostgresCategoryRepository(session=get_sync_session())
    return category_repo

def get_platform_repository() -> PlatformRepository:
    if _is_postgres_backend():
        return PostgresPlatformRepository(session=get_sync_session())
    return platform_repo

def get_watchlist_repository() -> WatchlistRepository:
    if _is_postgres_backend():
        return PostgresWatchlistRepository(session=get_sync_session())
    return watchlist_repo

def get_alert_repository() -> AlertRepository:
    if _is_postgres_backend():
        return PostgresAlertRepository(session=get_sync_session())
    return alert_repo

def get_notification_repository() -> NotificationRepository:
    if _is_postgres_backend():
        return PostgresNotificationRepository(session=get_sync_session())
    return notification_repo

def get_report_repository() -> ReportRepository:
    if _is_postgres_backend():
        return PostgresReportRepository(session=get_sync_session())
    return report_repo

def get_data_source_repository() -> DataSourceRepository:
    if _is_postgres_backend():
        return PostgresDataSourceRepository(session=get_sync_session())
    return data_source_repo

def get_settings_repository() -> SettingsRepository:
    if _is_postgres_backend():
        return PostgresSettingsRepository(session=get_sync_session())
    return settings_repo

def get_marketplace_product_repository() -> MarketplaceProductRepository:
    if _is_postgres_backend():
        return PostgresMarketplaceProductRepository(session=get_sync_session())
    return marketplace_product_repo

def get_shopify_repository() -> ShopifyRepository:
    if _is_postgres_backend():
        return PostgresShopifyRepository(session=get_sync_session())
    return shopify_repo

def get_unified_repository() -> UnifiedProductRepository:
    if _is_postgres_backend():
        return PostgresUnifiedProductRepository(session=get_sync_session())
    return unified_product_repo

def get_llm_usage_repository() -> LLMUsageRepository:
    if _is_postgres_backend():
        return PostgresLLMUsageRepository(session=get_sync_session())
    return llm_usage_repo

def get_data_quality_repository() -> DataQualityRepository:
    if _is_postgres_backend():
        return PostgresDataQualityRepository(session=get_sync_session())
    return data_quality_repo

def get_taxonomy_repository() -> TaxonomyRepository:
    if _is_postgres_backend():
        return PostgresTaxonomyRepository(session=get_sync_session())
    return taxonomy_repo

def get_market_intelligence_repository() -> MarketIntelligenceRepository:
    if _is_postgres_backend():
        return PostgresMarketIntelligenceRepository(session=get_sync_session())
    return market_intelligence_repo

# Service Providers
def get_shopify_service(
    repo: ShopifyRepository = Depends(get_shopify_repository)
) -> ShopifyService:
    if not hasattr(repo, "list_products"):
        repo = get_shopify_repository()
    return ShopifyService(repository=repo)

def get_llm_service(
    unified_repo: UnifiedProductRepository = Depends(get_unified_repository),
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository),
    usage_repo: LLMUsageRepository = Depends(get_llm_usage_repository)
) -> LLMService:
    return LLMService(
        unified_repo=unified_repo,
        marketplace_repo=marketplace_repo,
        usage_repo=usage_repo
    )

def get_data_quality_agent(
    repo: DataQualityRepository = Depends(get_data_quality_repository),
    llm_svc: LLMService = Depends(get_llm_service)
) -> DataQualityAgent:
    if not hasattr(repo, "save_validation_result"):
        repo = get_data_quality_repository()
    if not hasattr(llm_svc, "provider"):
        llm_svc = get_llm_service()
    return DataQualityAgent(
        repository=repo,
        llm_provider=getattr(llm_svc, "provider", None)
    )

def get_categorization_agent(
    repo: TaxonomyRepository = Depends(get_taxonomy_repository),
    llm_svc: LLMService = Depends(get_llm_service),
    usage_repo: LLMUsageRepository = Depends(get_llm_usage_repository)
) -> ProductCategorizationAgent:
    if not hasattr(repo, "get_category_by_id"):
        repo = get_taxonomy_repository()
    if not hasattr(llm_svc, "provider"):
        llm_svc = get_llm_service()
    if not hasattr(usage_repo, "record_usage"):
        usage_repo = get_llm_usage_repository()
    return ProductCategorizationAgent(
        repository=repo,
        llm_provider=getattr(llm_svc, "provider", None),
        llm_usage_repo=usage_repo
    )

def get_entity_matching_agent(
    unified_repo: UnifiedProductRepository = Depends(get_unified_repository),
    tax_repo: TaxonomyRepository = Depends(get_taxonomy_repository),
    llm_svc: LLMService = Depends(get_llm_service),
    usage_repo: LLMUsageRepository = Depends(get_llm_usage_repository)
) -> ProductEntityMatchingAgent:
    if not hasattr(unified_repo, "get_by_id"):
        unified_repo = get_unified_repository()
    if not hasattr(tax_repo, "get_category_by_id"):
        tax_repo = get_taxonomy_repository()
    if not hasattr(llm_svc, "provider"):
        llm_svc = get_llm_service()
    if not hasattr(usage_repo, "record_usage"):
        usage_repo = get_llm_usage_repository()
    return ProductEntityMatchingAgent(
        unified_repo=unified_repo,
        taxonomy_repo=tax_repo,
        llm_provider=getattr(llm_svc, "provider", None),
        llm_usage_repo=usage_repo
    )

def get_unified_intelligence_service(
    repo: UnifiedProductRepository = Depends(get_unified_repository),
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository),
    shopify_repo: ShopifyRepository = Depends(get_shopify_repository),
    dq_agent: DataQualityAgent = Depends(get_data_quality_agent),
    cat_agent: ProductCategorizationAgent = Depends(get_categorization_agent),
    tax_repo: TaxonomyRepository = Depends(get_taxonomy_repository),
    matching_agent: ProductEntityMatchingAgent = Depends(get_entity_matching_agent)
) -> UnifiedProductIntelligenceService:
    if not hasattr(repo, "get_by_id"):
        repo = get_unified_repository()
    if not hasattr(marketplace_repo, "get_product"):
        marketplace_repo = get_marketplace_product_repository()
    if not hasattr(shopify_repo, "list_products"):
        shopify_repo = get_shopify_repository()
    if not hasattr(dq_agent, "validate_product"):
        dq_agent = get_data_quality_agent()
    if not hasattr(cat_agent, "categorize"):
        cat_agent = get_categorization_agent()
    if not hasattr(tax_repo, "get_category_by_id"):
        tax_repo = get_taxonomy_repository()
    if not hasattr(matching_agent, "match_candidate"):
        matching_agent = get_entity_matching_agent()
    return UnifiedProductIntelligenceService(
        unified_repo=repo,
        daraz_repo=marketplace_repo,
        shopify_repo=shopify_repo,
        data_quality_agent=dq_agent,
        categorization_agent=cat_agent,
        taxonomy_repo=tax_repo,
        entity_matching_agent=matching_agent
    )


def get_scraper_repository() -> ScraperRepository:
    if _is_postgres_backend():
        return PostgresScraperRepository(session=get_sync_session())
    return scraper_repo


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
    products: ProductRepository = Depends(get_product_repository),
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository)
) -> CategoryService:
    return CategoryService(categories, products, marketplace_repo)

def get_platform_service(
    platforms: PlatformRepository = Depends(get_platform_repository),
    products: ProductRepository = Depends(get_product_repository),
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository)
) -> PlatformService:
    return PlatformService(platforms, products, marketplace_repo)

from backend.app.services.daraz_service import DarazService
from backend.app.services.live_signal_service import LiveSignalService

_daraz_service_instance: Optional[DarazService] = None
_live_signal_service_instance: Optional[LiveSignalService] = None

def get_daraz_service(
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository)
) -> DarazService:
    global _daraz_service_instance
    if not hasattr(marketplace_repo, "get_product"):
        marketplace_repo = get_marketplace_product_repository()
    if _daraz_service_instance is None:
        _daraz_service_instance = DarazService(marketplace_repo=marketplace_repo)
    else:
        _daraz_service_instance.marketplace_repo = marketplace_repo
    return _daraz_service_instance


def get_scraper_service(
    scraper_repo: ScraperRepository = Depends(get_scraper_repository),
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository),
    unified_repo: UnifiedProductRepository = Depends(get_unified_repository),
    unified_intel: UnifiedProductIntelligenceService = Depends(get_unified_intelligence_service),
    dq_agent: DataQualityAgent = Depends(get_data_quality_agent),
    daraz_svc: DarazService = Depends(get_daraz_service)
):
    if not hasattr(scraper_repo, "get_job"):
        scraper_repo = get_scraper_repository()
    if not hasattr(marketplace_repo, "get_product"):
        marketplace_repo = get_marketplace_product_repository()
    if not hasattr(unified_repo, "get_by_id"):
        unified_repo = get_unified_repository()
    if not hasattr(unified_intel, "ingest_daraz_product"):
        unified_intel = get_unified_intelligence_service()
    if not hasattr(dq_agent, "validate_product"):
        dq_agent = get_data_quality_agent()
    if not hasattr(daraz_svc, "search_products"):
        daraz_svc = get_daraz_service()

    from backend.app.services.scraper.bridge import ScraperIntegrationBridge
    from backend.app.services.scraper.service import ScraperService
    bridge = ScraperIntegrationBridge(
        scraper_repo=scraper_repo,
        marketplace_repo=marketplace_repo,
        unified_repo=unified_repo,
        unified_intelligence_svc=unified_intel,
        dq_agent=dq_agent,
        daraz_service=daraz_svc
    )
    return ScraperService(
        scraper_repo=scraper_repo,
        marketplace_repo=marketplace_repo,
        unified_repo=unified_repo,
        bridge=bridge
    )

def get_live_signal_service(
    daraz: DarazService = Depends(get_daraz_service)
) -> LiveSignalService:
    global _live_signal_service_instance
    if _live_signal_service_instance is None:
        _live_signal_service_instance = LiveSignalService(daraz_service=daraz)
    else:
        _live_signal_service_instance.daraz_service = daraz
    return _live_signal_service_instance

def get_dashboard_service(
    products: ProductRepository = Depends(get_product_repository),
    alerts: AlertRepository = Depends(get_alert_repository),
    platforms: PlatformRepository = Depends(get_platform_repository),
    daraz: DarazService = Depends(get_daraz_service),
    live_signals: LiveSignalService = Depends(get_live_signal_service),
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository)
) -> DashboardService:
    return DashboardService(
        product_repo=products,
        alert_repo=alerts,
        platform_repo=platforms,
        daraz_service=daraz,
        live_signal_service=live_signals,
        marketplace_repo=marketplace_repo
    )

def get_search_service(
    products: ProductRepository = Depends(get_product_repository),
    categories: CategoryRepository = Depends(get_category_repository),
    platforms: PlatformRepository = Depends(get_platform_repository),
    reports: ReportRepository = Depends(get_report_repository),
    alerts: AlertRepository = Depends(get_alert_repository),
    daraz: DarazService = Depends(get_daraz_service),
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository)
) -> SearchService:
    return SearchService(
        products, categories, platforms, reports, alerts,
        daraz_service=daraz, marketplace_repo=marketplace_repo
    )

def get_watchlist_service(
    watchlist: WatchlistRepository = Depends(get_watchlist_repository),
    products: ProductRepository = Depends(get_product_repository),
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository),
    unified_repo: UnifiedProductRepository = Depends(get_unified_repository)
) -> WatchlistService:
    return WatchlistService(
        watchlist_repo=watchlist,
        product_repo=products,
        marketplace_repo=marketplace_repo,
        unified_repo=unified_repo
    )

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
    products: ProductRepository = Depends(get_product_repository),
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository),
    platforms: PlatformRepository = Depends(get_platform_repository)
) -> ReportService:
    return ReportService(reports, products, marketplace_repo=marketplace_repo, platform_repo=platforms)

def get_data_source_service(
    sources: DataSourceRepository = Depends(get_data_source_repository),
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository)
) -> DataSourceService:
    return DataSourceService(sources, marketplace_repo=marketplace_repo)

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
        # Check for demo mode session
        if payload.get("role") == "demo" or payload.get("is_demo") is True:
            if not getattr(settings, "DEMO_MODE", False):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Demo access is currently disabled",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            from datetime import datetime, timezone
            return User(
                id=user_id or getattr(settings, "DEMO_USER_ID", "usr_demo_101"),
                email=payload.get("email", getattr(settings, "DEMO_USER_EMAIL", "judge@trendpulse.demo")),
                full_name="Hackathon Judge (Demo Mode)",
                hashed_password="",
                role="demo",
                workspace_id=getattr(settings, "DEMO_WORKSPACE_ID", "ws_demo_101"),
                is_active=True,
                is_verified=True,
                avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
                created_at=datetime.now(timezone.utc)
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

def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    users: UserRepository = Depends(get_user_repository),
    auth_persistence: AuthPersistenceRepository = Depends(get_auth_persistence_repository)
) -> Optional[User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        if payload.get("role") == "demo" or payload.get("is_demo") is True:
            if not getattr(settings, "DEMO_MODE", False):
                return None
            from datetime import datetime, timezone
            return User(
                id=user_id or getattr(settings, "DEMO_USER_ID", "usr_demo_101"),
                email=payload.get("email", getattr(settings, "DEMO_USER_EMAIL", "judge@trendpulse.demo")),
                full_name="Hackathon Judge (Demo Mode)",
                hashed_password="",
                role="demo",
                workspace_id=getattr(settings, "DEMO_WORKSPACE_ID", "ws_demo_101"),
                is_active=True,
                is_verified=True,
                avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
                created_at=datetime.now(timezone.utc)
            )
        return users.get_by_id(user_id)
    except JWTError:
        return None


def get_marketplace_search_orchestrator(
    scraper_repo: ScraperRepository = Depends(get_scraper_repository),
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository),
    unified_repo: UnifiedProductRepository = Depends(get_unified_repository),
    unified_intel: UnifiedProductIntelligenceService = Depends(get_unified_intelligence_service),
    dq_agent: DataQualityAgent = Depends(get_data_quality_agent),
    shopify_svc: ShopifyService = Depends(get_shopify_service)
):
    from backend.app.services.scraper.marketplace_search import (
        MarketplaceSearchOrchestrator,
        DarazMarketplaceSearchProvider,
        ScrapeGraphAIMarketplaceSearchProvider,
        ShopifyMarketplaceSearchProvider,
        MarketplaceType
    )
    if not hasattr(scraper_repo, "get_job"):
        scraper_repo = get_scraper_repository()
    if not hasattr(marketplace_repo, "get_product"):
        marketplace_repo = get_marketplace_product_repository()
    if not hasattr(unified_repo, "get_by_id"):
        unified_repo = get_unified_repository()
    if not hasattr(unified_intel, "ingest_daraz_product"):
        unified_intel = get_unified_intelligence_service()
    if not hasattr(dq_agent, "validate_product"):
        dq_agent = get_data_quality_agent()
    if not hasattr(shopify_svc, "list_products"):
        shopify_svc = get_shopify_service()

    daraz_provider = DarazMarketplaceSearchProvider()
    sg_provider = ScrapeGraphAIMarketplaceSearchProvider()
    shopify_provider = ShopifyMarketplaceSearchProvider(shopify_service=shopify_svc)

    providers = {
        MarketplaceType.DARAZ: daraz_provider,
        MarketplaceType.AMAZON: sg_provider,
        MarketplaceType.EBAY: sg_provider,
        MarketplaceType.SHOPIFY: shopify_provider
    }

    return MarketplaceSearchOrchestrator(
        providers=providers,
        dq_agent=dq_agent,
        scraper_repo=scraper_repo,
        marketplace_repo=marketplace_repo,
        unified_repo=unified_repo,
        unified_intelligence_svc=unified_intel
    )


from backend.app.services.social_intelligence_service import SocialIntelligenceService
from backend.app.services.ai_analyst_service import AIMarketAnalystService
from backend.app.services.market_intelligence_service import MarketIntelligenceService

_social_intelligence_service: Optional[SocialIntelligenceService] = None
_ai_market_analyst_service: Optional[AIMarketAnalystService] = None
_market_intelligence_service: Optional[MarketIntelligenceService] = None


def get_social_intelligence_service(
    repo: MarketIntelligenceRepository = Depends(get_market_intelligence_repository)
) -> SocialIntelligenceService:
    global _social_intelligence_service
    if not hasattr(repo, "save_social_signal"):
        repo = get_market_intelligence_repository()
    if _social_intelligence_service is None:
        _social_intelligence_service = SocialIntelligenceService(repo=repo)
    return _social_intelligence_service


def get_ai_market_analyst_service(
    llm_svc: LLMService = Depends(get_llm_service)
) -> AIMarketAnalystService:
    global _ai_market_analyst_service
    if _ai_market_analyst_service is None:
        _ai_market_analyst_service = AIMarketAnalystService(llm_service=llm_svc)
    return _ai_market_analyst_service


def get_market_intelligence_service(
    marketplace_repo: MarketplaceProductRepository = Depends(get_marketplace_product_repository),
    unified_repo: UnifiedProductRepository = Depends(get_unified_repository),
    social_service: SocialIntelligenceService = Depends(get_social_intelligence_service),
    ai_analyst: AIMarketAnalystService = Depends(get_ai_market_analyst_service),
    dq_agent: DataQualityAgent = Depends(get_data_quality_agent),
    market_intel_repo: MarketIntelligenceRepository = Depends(get_market_intelligence_repository),
    product_repo: ProductRepository = Depends(get_product_repository)
) -> MarketIntelligenceService:
    if not hasattr(marketplace_repo, "get_product"):
        marketplace_repo = get_marketplace_product_repository()
    if not hasattr(unified_repo, "get_by_id"):
        unified_repo = get_unified_repository()
    if not hasattr(social_service, "list_signals"):
        social_service = get_social_intelligence_service()
    if not hasattr(ai_analyst, "generate_product_analysis"):
        ai_analyst = get_ai_market_analyst_service()
    if not hasattr(dq_agent, "validate_product"):
        dq_agent = get_data_quality_agent()
    if not hasattr(market_intel_repo, "save_snapshot"):
        market_intel_repo = get_market_intelligence_repository()
    if not hasattr(product_repo, "list"):
        product_repo = get_product_repository()

    return MarketIntelligenceService(
        marketplace_repo=marketplace_repo,
        unified_repo=unified_repo,
        social_service=social_service,
        ai_analyst=ai_analyst,
        dq_agent=dq_agent,
        market_intel_repo=market_intel_repo,
        product_repo=product_repo
    )


