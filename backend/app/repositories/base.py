from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from backend.app.models.domain import (
    User, Workspace, WorkspaceMember, UserSession, EmailVerification, PasswordResetToken, LoginEvent,
    Product, Category, PlatformMetrics, Alert, Notification, Report, DataSource, UserSettings,
    SubscriptionPlan, UserSubscription, CreditAccount, CreditTransaction, CreditUsage,
    MarketplaceProduct, ProductMarketSnapshot, DarazAuthSession, DarazProviderHealth,
    DarazSeller, DarazCategory, DarazReview, DarazIngestionRun, DarazApiTelemetry, DarazDailyQuota, DarazTrainingDataset,
    ShopifyProduct, ShopifyProductSnapshot, ShopifyProviderHealth, ShopifySyncRun,
    UnifiedProduct, ProductPlatformListing, ProductMatchCandidate, ProductMatchAudit, ProductMatchDecision,
    LLMUsageRecord, AIAgent, AIAgentRun, AIAgentMemory, AIAgentMemoryEvent, DataQualityValidationResult,
    PublicDataQualityItem, PublicDataQualityStatsResponse,
    TaxonomyCategory, ProductTaxonomyAssignment, ProductTaxonomyCandidate,
    TrendObservation, TrendSignal, TrendSignalCandidate, TrendDetectionAudit, ProductTrendSummary, AgentTrendDetectionStats,
    AnomalyObservation, AnomalyDetection, AnomalyCandidate, AnomalyDetectionAudit, ProductAnomalySummary, AgentAnomalyDetectionStats,
    ProductRecommendation, RecommendationCandidate, RecommendationInteraction, RecommendationAudit, RecommendationScoreBreakdown, ProductRecommendationSummary, AgentRecommendationStats,
    MarketOpportunity, MarketOpportunityCandidate, MarketOpportunityAudit, MarketOpportunityScoreBreakdown, MarketOpportunitySummary, AgentMarketOpportunityStats,
    ScraperCrawlJob, RawScrapedPayload, ScraperMarketplaceHealth,
    MarketIntelligenceSnapshot, SocialSignal
)




class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]: ...
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]: ...
    @abstractmethod
    def get_by_verification_token(self, token: str) -> Optional[User]: ...
    @abstractmethod
    def get_by_reset_token(self, token: str) -> Optional[User]: ...
    @abstractmethod
    def create(self, user: User) -> User: ...
    @abstractmethod
    def update(self, user: User) -> User: ...
    @abstractmethod
    def delete(self, user_id: str) -> bool: ...

class WorkspaceRepository(ABC):
    @abstractmethod
    def get_by_id(self, workspace_id: str) -> Optional[Workspace]: ...
    @abstractmethod
    def get_by_owner_id(self, owner_id: str) -> Optional[Workspace]: ...
    @abstractmethod
    def create(self, workspace: Workspace) -> Workspace: ...
    @abstractmethod
    def update(self, workspace: Workspace) -> Workspace: ...
    @abstractmethod
    def add_member(self, member: WorkspaceMember) -> WorkspaceMember: ...
    @abstractmethod
    def get_members(self, workspace_id: str) -> List[WorkspaceMember]: ...
    @abstractmethod
    def delete(self, workspace_id: str) -> bool: ...

class AuthPersistenceRepository(ABC):
    @abstractmethod
    def create_session(self, session: UserSession) -> UserSession: ...
    @abstractmethod
    def get_session(self, token_hash: str) -> Optional[UserSession]: ...
    @abstractmethod
    def revoke_session(self, token_hash: str) -> bool: ...
    @abstractmethod
    def revoke_all_user_sessions(self, user_id: str) -> int: ...
    @abstractmethod
    def create_email_verification(self, verification: EmailVerification) -> EmailVerification: ...
    @abstractmethod
    def get_email_verification(self, token: str) -> Optional[EmailVerification]: ...
    @abstractmethod
    def mark_email_verification_used(self, token: str) -> bool: ...
    @abstractmethod
    def invalidate_user_verifications(self, user_id: str) -> int: ...
    @abstractmethod
    def create_password_reset_token(self, reset_token: PasswordResetToken) -> PasswordResetToken: ...
    @abstractmethod
    def get_password_reset_token(self, token: str) -> Optional[PasswordResetToken]: ...
    @abstractmethod
    def mark_password_reset_token_used(self, token: str) -> bool: ...
    @abstractmethod
    def record_login_event(self, event: LoginEvent) -> LoginEvent: ...
    @abstractmethod
    def list_login_events(self, user_id: Optional[str] = None, email: Optional[str] = None) -> List[LoginEvent]: ...

class SubscriptionRepository(ABC):
    @abstractmethod
    def list_plans(self, active_only: bool = True) -> List[SubscriptionPlan]: ...
    @abstractmethod
    def get_plan_by_id(self, plan_id: str) -> Optional[SubscriptionPlan]: ...
    @abstractmethod
    def get_plan_by_slug(self, slug: str) -> Optional[SubscriptionPlan]: ...
    @abstractmethod
    def get_user_subscription(self, user_id: str) -> Optional[UserSubscription]: ...
    @abstractmethod
    def create_user_subscription(self, subscription: UserSubscription) -> UserSubscription: ...
    @abstractmethod
    def update_user_subscription(self, subscription: UserSubscription) -> UserSubscription: ...

class CreditRepository(ABC):
    @abstractmethod
    def get_or_create_account(self, user_id: str) -> CreditAccount: ...
    @abstractmethod
    def get_account(self, user_id: str) -> Optional[CreditAccount]: ...
    @abstractmethod
    def update_account_balance(self, user_id: str, new_balance: int, delta_granted: int, delta_used: int) -> CreditAccount: ...
    @abstractmethod
    def create_transaction(self, tx: CreditTransaction) -> CreditTransaction: ...
    @abstractmethod
    def get_transaction_by_reference(self, user_id: str, reference_type: str, reference_id: str) -> Optional[CreditTransaction]: ...
    @abstractmethod
    def list_transactions(self, user_id: str, limit: int = 50, offset: int = 0) -> List[CreditTransaction]: ...
    @abstractmethod
    def record_usage(self, usage: CreditUsage) -> CreditUsage: ...
    @abstractmethod
    def get_usage_by_reference(self, user_id: str, reference_type: str, reference_id: str) -> Optional[CreditUsage]: ...
    @abstractmethod
    def list_usage(self, user_id: str, limit: int = 50, offset: int = 0) -> List[CreditUsage]: ...

class ProductRepository(ABC):
    @abstractmethod
    def get_by_id(self, product_id: str) -> Optional[Product]: ...
    @abstractmethod
    def list(self, category: Optional[str] = None, platform: Optional[str] = None, search: Optional[str] = None, sort_by: Optional[str] = None) -> List[Product]: ...
    @abstractmethod
    def update(self, product: Product) -> Product: ...

class CategoryRepository(ABC):
    @abstractmethod
    def list(self) -> List[Category]: ...
    @abstractmethod
    def get_by_id(self, category_id: str) -> Optional[Category]: ...

class PlatformRepository(ABC):
    @abstractmethod
    def list(self) -> List[PlatformMetrics]: ...
    @abstractmethod
    def get_by_slug(self, slug: str) -> Optional[PlatformMetrics]: ...

class WatchlistRepository(ABC):
    @abstractmethod
    def list_product_ids(self, user_id: str) -> List[str]: ...
    @abstractmethod
    def add(self, user_id: str, product_id: str) -> bool: ...
    @abstractmethod
    def remove(self, user_id: str, product_id: str) -> bool: ...
    @abstractmethod
    def is_in_watchlist(self, user_id: str, product_id: str) -> bool: ...

class AlertRepository(ABC):
    @abstractmethod
    def list(self, severity: Optional[str] = None, unread_only: bool = False) -> List[Alert]: ...
    @abstractmethod
    def get_by_id(self, alert_id: str) -> Optional[Alert]: ...
    @abstractmethod
    def create(self, alert: Alert) -> Alert: ...
    @abstractmethod
    def mark_read(self, alert_id: str) -> Optional[Alert]: ...
    @abstractmethod
    def resolve(self, alert_id: str) -> Optional[Alert]: ...

class NotificationRepository(ABC):
    @abstractmethod
    def list(self, unread_only: bool = False) -> List[Notification]: ...
    @abstractmethod
    def mark_read(self, notification_id: str) -> Optional[Notification]: ...
    @abstractmethod
    def mark_all_read(self) -> int: ...

class ReportRepository(ABC):
    @abstractmethod
    def list(self) -> List[Report]: ...
    @abstractmethod
    def get_by_id(self, report_id: str) -> Optional[Report]: ...
    @abstractmethod
    def create(self, report: Report) -> Report: ...
    @abstractmethod
    def update(self, report: Report) -> Report: ...

class DataSourceRepository(ABC):
    @abstractmethod
    def list(self) -> List[DataSource]: ...
    @abstractmethod
    def get_by_slug(self, slug: str) -> Optional[DataSource]: ...
    @abstractmethod
    def update_status(self, slug: str, status: str) -> Optional[DataSource]: ...
    @abstractmethod
    def update(self, data_source: DataSource) -> DataSource: ...

class SettingsRepository(ABC):
    @abstractmethod
    def get_by_user_id(self, user_id: str) -> Optional[UserSettings]: ...
    @abstractmethod
    def update(self, settings: UserSettings) -> UserSettings: ...

class MarketplaceProductRepository(ABC):
    @abstractmethod
    def upsert_product(self, product: MarketplaceProduct) -> MarketplaceProduct: ...
    @abstractmethod
    def batch_upsert_products(self, products: List[MarketplaceProduct]) -> List[MarketplaceProduct]: ...
    @abstractmethod
    def get_product(self, platform: str, product_id: str) -> Optional[MarketplaceProduct]: ...
    @abstractmethod
    def list_products(
        self,
        platform: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[MarketplaceProduct]: ...
    @abstractmethod
    def count_products(self, platform: Optional[str] = None, category: Optional[str] = None) -> int: ...
    @abstractmethod
    def create_snapshot(self, snapshot: ProductMarketSnapshot) -> ProductMarketSnapshot: ...
    @abstractmethod
    def batch_create_snapshots(self, snapshots: List[ProductMarketSnapshot]) -> List[ProductMarketSnapshot]: ...
    @abstractmethod
    def get_snapshots(self, platform: str, product_id: str, limit: int = 50) -> List[ProductMarketSnapshot]: ...
    @abstractmethod
    def get_latest_sync_metadata(self, platform: str = "daraz") -> Dict[str, Any]: ...
    @abstractmethod
    def save_auth_session(self, session: DarazAuthSession) -> DarazAuthSession: ...
    @abstractmethod
    def get_auth_session(self, seller_id_or_account: Optional[str] = None) -> Optional[DarazAuthSession]: ...
    @abstractmethod
    def list_auth_sessions(self) -> List[DarazAuthSession]: ...
    @abstractmethod
    def get_provider_health(self, provider_name: str) -> Optional[DarazProviderHealth]: ...
    @abstractmethod
    def update_provider_health(self, health: DarazProviderHealth) -> DarazProviderHealth: ...
    @abstractmethod
    def list_provider_health(self) -> List[DarazProviderHealth]: ...
    @abstractmethod
    def upsert_seller(self, seller: DarazSeller) -> DarazSeller: ...
    @abstractmethod
    def get_seller(self, seller_id: str) -> Optional[DarazSeller]: ...
    @abstractmethod
    def list_sellers(self, limit: int = 50, offset: int = 0) -> List[DarazSeller]: ...
    @abstractmethod
    def upsert_category(self, category: DarazCategory) -> DarazCategory: ...
    @abstractmethod
    def get_category(self, category_id: str) -> Optional[DarazCategory]: ...
    @abstractmethod
    def list_categories(self, parent_id: Optional[str] = None) -> List[DarazCategory]: ...
    @abstractmethod
    def create_review(self, review: DarazReview) -> DarazReview: ...
    @abstractmethod
    def list_reviews(self, product_id: str, limit: int = 50) -> List[DarazReview]: ...
    @abstractmethod
    def create_ingestion_run(self, run: DarazIngestionRun) -> DarazIngestionRun: ...
    @abstractmethod
    def update_ingestion_run(self, run: DarazIngestionRun) -> DarazIngestionRun: ...
    @abstractmethod
    def get_ingestion_run(self, run_id: str) -> Optional[DarazIngestionRun]: ...
    @abstractmethod
    def list_ingestion_runs(self, limit: int = 50) -> List[DarazIngestionRun]: ...
    @abstractmethod
    def record_api_telemetry(self, telemetry: DarazApiTelemetry) -> DarazApiTelemetry: ...
    @abstractmethod
    def get_api_telemetry(self, limit: int = 100) -> List[DarazApiTelemetry]: ...
    @abstractmethod
    def get_or_create_daily_quota(self, date: Optional[str] = None, daily_limit: int = 6000000) -> DarazDailyQuota: ...
    @abstractmethod
    def increment_daily_quota(self, date: Optional[str] = None, count: int = 1, is_rate_limited: bool = False) -> DarazDailyQuota: ...
    @abstractmethod
    def add_training_dataset_item(self, item: DarazTrainingDataset) -> DarazTrainingDataset: ...
    @abstractmethod
    def list_training_dataset(self, category: Optional[str] = None, limit: int = 100) -> List[DarazTrainingDataset]: ...

class ShopifyRepository(ABC):
    @abstractmethod
    def upsert_product(self, product: ShopifyProduct) -> ShopifyProduct: ...
    @abstractmethod
    def batch_upsert_products(self, products: List[ShopifyProduct]) -> List[ShopifyProduct]: ...
    @abstractmethod
    def get_product(self, store_domain: str, product_id: str) -> Optional[ShopifyProduct]: ...
    @abstractmethod
    def get_product_by_id(self, id: str) -> Optional[ShopifyProduct]: ...
    @abstractmethod
    def list_products(
        self,
        store_domain: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ShopifyProduct]: ...
    @abstractmethod
    def count_products(
        self,
        store_domain: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> int: ...
    @abstractmethod
    def create_snapshot(self, snapshot: ShopifyProductSnapshot) -> ShopifyProductSnapshot: ...
    @abstractmethod
    def batch_create_snapshots(self, snapshots: List[ShopifyProductSnapshot]) -> List[ShopifyProductSnapshot]: ...
    @abstractmethod
    def get_snapshots(self, store_domain: str, product_id: str, limit: int = 50) -> List[ShopifyProductSnapshot]: ...
    @abstractmethod
    def get_provider_health(self, provider_name: str) -> Optional[ShopifyProviderHealth]: ...
    @abstractmethod
    def list_provider_health(self) -> List[ShopifyProviderHealth]: ...
    @abstractmethod
    def update_provider_health(self, health: ShopifyProviderHealth) -> ShopifyProviderHealth: ...
    @abstractmethod
    def record_sync_run(self, sync_run: ShopifySyncRun) -> ShopifySyncRun: ...
    @abstractmethod
    def list_sync_runs(self, store_domain: Optional[str] = None, limit: int = 20) -> List[ShopifySyncRun]: ...
    @abstractmethod
    def get_latest_sync_metadata(self, store_domain: Optional[str] = None) -> Dict[str, Any]: ...

class UnifiedProductRepository(ABC):
    @abstractmethod
    def upsert_unified_product(self, product: UnifiedProduct) -> UnifiedProduct: ...
    @abstractmethod
    def get_unified_product(self, unified_product_id: str) -> Optional[UnifiedProduct]: ...
    @abstractmethod
    def find_by_normalized_name(self, normalized_name: str) -> List[UnifiedProduct]: ...
    @abstractmethod
    def find_by_brand(self, brand: str) -> List[UnifiedProduct]: ...
    @abstractmethod
    def list_unified_products(
        self,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        platform: Optional[str] = None,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        available: Optional[bool] = None,
        min_rating: Optional[float] = None,
        sort_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[UnifiedProduct]: ...
    @abstractmethod
    def count_unified_products(
        self,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        platform: Optional[str] = None,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        available: Optional[bool] = None,
        min_rating: Optional[float] = None
    ) -> int: ...
    @abstractmethod
    def upsert_platform_listing(self, listing: ProductPlatformListing) -> ProductPlatformListing: ...
    @abstractmethod
    def get_platform_listing(self, platform: str, platform_product_id: str, store_domain: Optional[str] = None) -> Optional[ProductPlatformListing]: ...
    @abstractmethod
    def list_listings_for_product(self, unified_product_id: str) -> List[ProductPlatformListing]: ...
    @abstractmethod
    def list_all_listings(self) -> List[ProductPlatformListing]: ...
    @abstractmethod
    def record_match_audit(self, audit: ProductMatchAudit) -> ProductMatchAudit: ...
    @abstractmethod
    def get_match_audit(self, unified_product_id: str) -> Optional[ProductMatchAudit]: ...
    @abstractmethod
    def list_match_audits(self, unified_product_id: Optional[str] = None, limit: int = 50) -> List[ProductMatchAudit]: ...
    @abstractmethod
    def record_match_candidate(self, candidate: ProductMatchCandidate) -> ProductMatchCandidate: ...
    @abstractmethod
    def get_match_candidate(self, candidate_id: str) -> Optional[ProductMatchCandidate]: ...
    @abstractmethod
    def update_match_candidate(self, candidate: ProductMatchCandidate) -> ProductMatchCandidate: ...
    @abstractmethod
    def list_match_candidates(self, unified_product_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[ProductMatchCandidate]: ...
    @abstractmethod
    def record_match_decision(self, decision: ProductMatchDecision) -> ProductMatchDecision: ...
    @abstractmethod
    def get_match_decision(self, decision_id: str) -> Optional[ProductMatchDecision]: ...
    @abstractmethod
    def list_match_decisions(self, product_id: Optional[str] = None, unified_product_id: Optional[str] = None, limit: int = 50) -> List[ProductMatchDecision]: ...

class LLMUsageRepository(ABC):
    @abstractmethod
    def record_usage(self, record: LLMUsageRecord) -> LLMUsageRecord: ...
    @abstractmethod
    def list_usage(
        self,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        provider: Optional[str] = None,
        request_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[LLMUsageRecord]: ...
    @abstractmethod
    def get_summary(self, user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> Dict[str, Any]: ...

class DataQualityRepository(ABC):
    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[AIAgent]: ...
    @abstractmethod
    def upsert_agent(self, agent: AIAgent) -> AIAgent: ...
    @abstractmethod
    def create_agent_run(self, run: AIAgentRun) -> AIAgentRun: ...
    @abstractmethod
    def update_agent_run(self, run: AIAgentRun) -> AIAgentRun: ...
    @abstractmethod
    def get_agent_run(self, run_id: str) -> Optional[AIAgentRun]: ...
    @abstractmethod
    def list_agent_runs(self, agent_id: str, workspace_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[AIAgentRun]: ...
    @abstractmethod
    def get_memory(self, agent_id: str, memory_type: str, memory_key: str) -> Optional[AIAgentMemory]: ...
    @abstractmethod
    def upsert_memory(self, memory: AIAgentMemory) -> AIAgentMemory: ...
    @abstractmethod
    def list_memories(self, agent_id: str, memory_type: Optional[str] = None) -> List[AIAgentMemory]: ...
    @abstractmethod
    def record_memory_event(self, event: AIAgentMemoryEvent) -> AIAgentMemoryEvent: ...
    @abstractmethod
    def list_memory_events(self, agent_id: str, memory_id: Optional[str] = None, limit: int = 50) -> List[AIAgentMemoryEvent]: ...
    @abstractmethod
    def save_validation_result(self, result: DataQualityValidationResult) -> DataQualityValidationResult: ...
    @abstractmethod
    def get_validation_result(self, result_id: str) -> Optional[DataQualityValidationResult]: ...
    @abstractmethod
    def list_validation_results(
        self,
        workspace_id: Optional[str] = None,
        platform: Optional[str] = None,
        classification: Optional[str] = None,
        source_provider: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DataQualityValidationResult]: ...
    @abstractmethod
    def count_validation_results(
        self,
        workspace_id: Optional[str] = None,
        platform: Optional[str] = None,
        classification: Optional[str] = None,
        source_provider: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None
    ) -> int: ...
    @abstractmethod
    def get_quality_summary(self, workspace_id: Optional[str] = None) -> Dict[str, Any]: ...
    @abstractmethod
    def get_public_feed(
        self,
        platform: Optional[str] = None,
        provider: Optional[str] = None,
        classification: Optional[str] = None,
        normalized_category: Optional[str] = None,
        rejection_reason: Optional[str] = None,
        search: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sort_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[PublicDataQualityItem], int]: ...

    @abstractmethod
    def get_public_stats(self) -> PublicDataQualityStatsResponse: ...
    @abstractmethod
    def get_product_validation_history(
        self,
        platform: str,
        platform_product_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[DataQualityValidationResult]: ...
    @abstractmethod
    def clear(self) -> None: ...


class TaxonomyRepository(ABC):
    @abstractmethod
    def get_category_by_id(self, category_id: str) -> Optional[TaxonomyCategory]: ...
    @abstractmethod
    def get_category_by_slug(self, slug: str) -> Optional[TaxonomyCategory]: ...
    @abstractmethod
    def list_categories(self, parent_id: Optional[str] = None, level: Optional[int] = None) -> List[TaxonomyCategory]: ...
    @abstractmethod
    def get_taxonomy_tree(self) -> List[TaxonomyCategory]: ...
    @abstractmethod
    def search_categories(self, query: str, limit: int = 20) -> List[Dict[str, Any]]: ...
    @abstractmethod
    def create_category(self, category: TaxonomyCategory) -> TaxonomyCategory: ...
    @abstractmethod
    def update_category(self, category: TaxonomyCategory) -> TaxonomyCategory: ...
    @abstractmethod
    def get_assignment_by_unified_product_id(self, unified_product_id: str) -> Optional[ProductTaxonomyAssignment]: ...
    @abstractmethod
    def get_assignment_history(self, unified_product_id: str, limit: int = 50) -> List[ProductTaxonomyAssignment]: ...
    @abstractmethod
    def upsert_assignment(self, assignment: ProductTaxonomyAssignment) -> ProductTaxonomyAssignment: ...
    @abstractmethod
    def create_candidate(self, candidate: ProductTaxonomyCandidate) -> ProductTaxonomyCandidate: ...
    @abstractmethod
    def list_candidates(self, limit: int = 50, offset: int = 0) -> List[ProductTaxonomyCandidate]: ...
    @abstractmethod
    def get_category_product_counts(self) -> Dict[str, int]: ...
    @abstractmethod
    def get_memory(self, agent_id: str, memory_type: str, memory_key: str) -> Optional[AIAgentMemory]: ...
    @abstractmethod
    def upsert_memory(self, memory: AIAgentMemory) -> AIAgentMemory: ...
    @abstractmethod
    def list_memory(self, agent_id: str, memory_type: Optional[str] = None) -> List[AIAgentMemory]: ...
    @abstractmethod
    def record_memory_event(self, event: AIAgentMemoryEvent) -> AIAgentMemoryEvent: ...
    @abstractmethod
    def get_memory_events(self, agent_id: str, memory_id: Optional[str] = None, limit: int = 50) -> List[AIAgentMemoryEvent]: ...
    @abstractmethod
    def clear(self) -> None: ...


class TrendDetectionRepository(ABC):
    @abstractmethod
    def record_observation(self, observation: TrendObservation) -> TrendObservation: ...
    @abstractmethod
    def batch_record_observations(self, observations: List[TrendObservation]) -> List[TrendObservation]: ...
    @abstractmethod
    def list_observations(
        self,
        unified_product_id: str,
        metric_type: Optional[str] = None,
        platform: Optional[str] = None,
        start_time: Optional[datetime] = None,
        limit: int = 50
    ) -> List[TrendObservation]: ...
    @abstractmethod
    def upsert_signal(self, signal: TrendSignal) -> TrendSignal: ...
    @abstractmethod
    def get_signal_by_fingerprint(self, fingerprint: str) -> Optional[TrendSignal]: ...
    @abstractmethod
    def list_signals(
        self,
        unified_product_id: Optional[str] = None,
        signal_type: Optional[str] = None,
        direction: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        min_strength: Optional[float] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TrendSignal]: ...
    @abstractmethod
    def count_signals(
        self,
        unified_product_id: Optional[str] = None,
        signal_type: Optional[str] = None,
        direction: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None
    ) -> int: ...
    @abstractmethod
    def create_candidate(self, candidate: TrendSignalCandidate) -> TrendSignalCandidate: ...
    @abstractmethod
    def get_candidate(self, candidate_id: str) -> Optional[TrendSignalCandidate]: ...
    @abstractmethod
    def list_candidates(
        self,
        status: Optional[str] = None,
        candidate_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TrendSignalCandidate]: ...
    @abstractmethod
    def resolve_candidate(
        self,
        candidate_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[TrendSignalCandidate]: ...
    @abstractmethod
    def record_audit(self, audit: TrendDetectionAudit) -> TrendDetectionAudit: ...
    @abstractmethod
    def list_audits(
        self,
        product_id: Optional[str] = None,
        agent_id: str = "agent_trend_detection",
        limit: int = 50
    ) -> List[TrendDetectionAudit]: ...
    @abstractmethod
    def get_trend_stats(self) -> AgentTrendDetectionStats: ...
    @abstractmethod
    def clear(self) -> None: ...


class AnomalyDetectionRepository(ABC):
    @abstractmethod
    def record_observation(self, observation: AnomalyObservation) -> AnomalyObservation: ...
    @abstractmethod
    def batch_record_observations(self, observations: List[AnomalyObservation]) -> List[AnomalyObservation]: ...
    @abstractmethod
    def list_observations(
        self,
        unified_product_id: str,
        metric_type: Optional[str] = None,
        platform: Optional[str] = None,
        start_time: Optional[datetime] = None,
        limit: int = 50
    ) -> List[AnomalyObservation]: ...
    @abstractmethod
    def upsert_anomaly(self, anomaly: AnomalyDetection) -> AnomalyDetection: ...
    @abstractmethod
    def get_anomaly_by_fingerprint(self, fingerprint: str) -> Optional[AnomalyDetection]: ...
    @abstractmethod
    def list_anomalies(
        self,
        unified_product_id: Optional[str] = None,
        anomaly_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        min_score: Optional[float] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AnomalyDetection]: ...
    @abstractmethod
    def count_anomalies(
        self,
        unified_product_id: Optional[str] = None,
        anomaly_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        platform: Optional[str] = None
    ) -> int: ...
    @abstractmethod
    def create_candidate(self, candidate: AnomalyCandidate) -> AnomalyCandidate: ...
    @abstractmethod
    def get_candidate(self, candidate_id: str) -> Optional[AnomalyCandidate]: ...
    @abstractmethod
    def list_candidates(
        self,
        status: Optional[str] = None,
        candidate_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AnomalyCandidate]: ...
    @abstractmethod
    def resolve_candidate(
        self,
        candidate_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[AnomalyCandidate]: ...
    @abstractmethod
    def record_audit(self, audit: AnomalyDetectionAudit) -> AnomalyDetectionAudit: ...
    @abstractmethod
    def list_audits(
        self,
        product_id: Optional[str] = None,
        agent_id: str = "agent_anomaly_detection",
        limit: int = 50
    ) -> List[AnomalyDetectionAudit]: ...
    @abstractmethod
    def get_anomaly_stats(self) -> AgentAnomalyDetectionStats: ...
    @abstractmethod
    def clear(self) -> None: ...


class RecommendationRepository(ABC):
    @abstractmethod
    def save_recommendation(self, recommendation: ProductRecommendation) -> ProductRecommendation: ...
    @abstractmethod
    def batch_save_recommendations(self, recommendations: List[ProductRecommendation]) -> List[ProductRecommendation]: ...
    @abstractmethod
    def get_recommendation(self, recommendation_id: str) -> Optional[ProductRecommendation]: ...
    @abstractmethod
    def get_recommendation_by_fingerprint(self, fingerprint: str) -> Optional[ProductRecommendation]: ...
    @abstractmethod
    def list_recommendations(
        self,
        unified_product_id: Optional[str] = None,
        recommendation_type: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        platform: Optional[str] = None,
        status: Optional[str] = "active",
        min_score: Optional[float] = None,
        min_confidence: Optional[float] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = "score_desc",
        limit: int = 50,
        offset: int = 0
    ) -> List[ProductRecommendation]: ...
    @abstractmethod
    def count_recommendations(
        self,
        unified_product_id: Optional[str] = None,
        recommendation_type: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        platform: Optional[str] = None,
        status: Optional[str] = "active",
        min_score: Optional[float] = None,
        min_confidence: Optional[float] = None,
        search: Optional[str] = None
    ) -> int: ...
    @abstractmethod
    def list_recommendations_for_product(
        self,
        unified_product_id: str,
        recommendation_type: Optional[str] = None,
        limit: int = 10
    ) -> List[ProductRecommendation]: ...
    @abstractmethod
    def create_candidate(self, candidate: RecommendationCandidate) -> RecommendationCandidate: ...
    @abstractmethod
    def get_candidate(self, candidate_id: str) -> Optional[RecommendationCandidate]: ...
    @abstractmethod
    def list_candidates(
        self,
        status: Optional[str] = None,
        candidate_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[RecommendationCandidate]: ...
    @abstractmethod
    def resolve_candidate(
        self,
        candidate_id: str,
        status: str,
        reviewed_by: Optional[str] = None
    ) -> Optional[RecommendationCandidate]: ...
    @abstractmethod
    def record_interaction(self, interaction: RecommendationInteraction) -> RecommendationInteraction: ...
    @abstractmethod
    def list_interactions(
        self,
        user_id: Optional[str] = None,
        product_id: Optional[str] = None,
        interaction_type: Optional[str] = None,
        limit: int = 50
    ) -> List[RecommendationInteraction]: ...
    @abstractmethod
    def record_audit(self, audit: RecommendationAudit) -> RecommendationAudit: ...
    @abstractmethod
    def list_audits(
        self,
        product_id: Optional[str] = None,
        agent_id: str = "agent_recommendation_engine",
        limit: int = 50
    ) -> List[RecommendationAudit]: ...
    @abstractmethod
    def get_recommendation_stats(self) -> AgentRecommendationStats: ...
    @abstractmethod
    def upsert_memory(self, memory: AIAgentMemory) -> AIAgentMemory: ...
    @abstractmethod
    def get_memory(self, agent_id: str, memory_type: str, memory_key: str) -> Optional[AIAgentMemory]: ...
    @abstractmethod
    def list_memories(self, agent_id: str, memory_type: Optional[str] = None) -> List[AIAgentMemory]: ...
    @abstractmethod
    def record_memory_event(self, event: AIAgentMemoryEvent) -> AIAgentMemoryEvent: ...
    @abstractmethod
    def list_memory_events(self, agent_id: str, memory_id: Optional[str] = None) -> List[AIAgentMemoryEvent]: ...
    @abstractmethod
    def clear(self) -> None: ...


class MarketOpportunityRepository(ABC):
    @abstractmethod
    def save_opportunity(self, opportunity: MarketOpportunity) -> MarketOpportunity: ...
    @abstractmethod
    def get_opportunity(self, id: str) -> Optional[MarketOpportunity]: ...
    @abstractmethod
    def list_opportunities(
        self,
        unified_product_id: Optional[str] = None,
        opportunity_type: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        min_score: Optional[float] = None,
        min_confidence: Optional[float] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[MarketOpportunity]: ...
    @abstractmethod
    def count_opportunities(
        self,
        unified_product_id: Optional[str] = None,
        opportunity_type: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        min_score: Optional[float] = None,
        min_confidence: Optional[float] = None,
        search: Optional[str] = None
    ) -> int: ...
    @abstractmethod
    def list_opportunities_for_product(self, unified_product_id: str) -> List[MarketOpportunity]: ...
    @abstractmethod
    def list_opportunities_for_category(self, category: str) -> List[MarketOpportunity]: ...
    @abstractmethod
    def create_candidate(self, candidate: MarketOpportunityCandidate) -> MarketOpportunityCandidate: ...
    @abstractmethod
    def get_candidate(self, id: str) -> Optional[MarketOpportunityCandidate]: ...
    @abstractmethod
    def list_candidates(
        self,
        status: Optional[str] = None,
        candidate_type: Optional[str] = None,
        limit: int = 50
    ) -> List[MarketOpportunityCandidate]: ...
    @abstractmethod
    def resolve_candidate(
        self,
        candidate_id: str,
        status: str,
        reviewed_by: Optional[str] = None
    ) -> Optional[MarketOpportunityCandidate]: ...
    @abstractmethod
    def record_audit(self, audit: MarketOpportunityAudit) -> MarketOpportunityAudit: ...
    @abstractmethod
    def list_audits(
        self,
        product_id: Optional[str] = None,
        opportunity_id: Optional[str] = None,
        agent_id: str = "agent_market_opportunity_intelligence",
        limit: int = 50
    ) -> List[MarketOpportunityAudit]: ...
    @abstractmethod
    def get_opportunity_stats(self) -> AgentMarketOpportunityStats: ...
    @abstractmethod
    def upsert_memory(self, memory: AIAgentMemory) -> AIAgentMemory: ...
    @abstractmethod
    def get_memory(self, agent_id: str, memory_type: str, memory_key: str) -> Optional[AIAgentMemory]: ...
    @abstractmethod
    def list_memories(self, agent_id: str, memory_type: Optional[str] = None) -> List[AIAgentMemory]: ...
    @abstractmethod
    def record_memory_event(self, event: AIAgentMemoryEvent) -> AIAgentMemoryEvent: ...
    @abstractmethod
    def list_memory_events(self, agent_id: str, memory_id: Optional[str] = None) -> List[AIAgentMemoryEvent]: ...
    @abstractmethod
    def clear(self) -> None: ...


class ScraperRepository(ABC):
    @abstractmethod
    def create_job(self, job: ScraperCrawlJob) -> ScraperCrawlJob: ...
    @abstractmethod
    def get_job(self, job_id: str) -> Optional[ScraperCrawlJob]: ...
    @abstractmethod
    def update_job(self, job: ScraperCrawlJob) -> ScraperCrawlJob: ...
    @abstractmethod
    def list_jobs(
        self,
        marketplace: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ScraperCrawlJob]: ...
    @abstractmethod
    def count_jobs(
        self,
        marketplace: Optional[str] = None,
        status: Optional[str] = None
    ) -> int: ...
    @abstractmethod
    def save_raw_payload(self, payload: RawScrapedPayload) -> RawScrapedPayload: ...
    @abstractmethod
    def get_raw_payload(self, marketplace: str, product_id: str) -> Optional[RawScrapedPayload]: ...
    @abstractmethod
    def list_raw_payloads(
        self,
        marketplace: Optional[str] = None,
        crawl_job_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[RawScrapedPayload]: ...
    @abstractmethod
    def record_marketplace_health(self, health: ScraperMarketplaceHealth) -> ScraperMarketplaceHealth: ...
    @abstractmethod
    def get_marketplace_health(self, marketplace: str) -> Optional[ScraperMarketplaceHealth]: ...
    @abstractmethod
    def list_marketplace_health(self) -> List[ScraperMarketplaceHealth]: ...
    @abstractmethod
    def clear(self) -> None: ...


class MarketIntelligenceRepository(ABC):
    @abstractmethod
    def save_snapshot(self, snapshot: MarketIntelligenceSnapshot) -> MarketIntelligenceSnapshot: ...

    @abstractmethod
    def get_latest_snapshot(self, product_id: str, marketplace: Optional[str] = None) -> Optional[MarketIntelligenceSnapshot]: ...

    @abstractmethod
    def list_snapshots(
        self,
        product_id: Optional[str] = None,
        marketplace: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[MarketIntelligenceSnapshot]: ...

    @abstractmethod
    def save_social_signal(self, signal: SocialSignal) -> SocialSignal: ...

    @abstractmethod
    def list_social_signals(
        self,
        platform: Optional[str] = None,
        product_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[SocialSignal]: ...

    @abstractmethod
    def clear(self) -> None: ...











