from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, func
import os
from backend.app.core.config import settings

from backend.app.models.domain import (
    User, Workspace, WorkspaceMember, UserSession, EmailVerification, PasswordResetToken, LoginEvent,
    Product, Category, PlatformMetrics, Alert, Notification, Report, DataSource, UserSettings,
    SubscriptionPlan, UserSubscription, CreditAccount, CreditTransaction, CreditUsage,
    MarketplaceProduct, ProductMarketSnapshot, DarazAuthSession, DarazProviderHealth,
    DarazSeller, DarazCategory, DarazReview, DarazIngestionRun, DarazApiTelemetry, DarazDailyQuota, DarazTrainingDataset,
    ShopifyProduct, ShopifyProductSnapshot, ShopifyProviderHealth, ShopifySyncRun,
    UnifiedProduct, ProductPlatformListing, ProductMatchCandidate, ProductMatchAudit, ProductMatchDecision,
    LLMUsageRecord, AIAgent, AIAgentRun, AIAgentMemory, AIAgentMemoryEvent, DataQualityValidationResult,
    PublicDataQualityItem, PublicDataQualityStatsResponse, DataQualityRuleViolation,
    TaxonomyCategory, ProductTaxonomyAssignment, ProductTaxonomyCandidate,
    ScraperCrawlJob, RawScrapedPayload, ScraperMarketplaceHealth,
    MarketIntelligenceSnapshot, SocialSignal
)

from backend.app.repositories.base import (
    UserRepository, WorkspaceRepository, AuthPersistenceRepository, SubscriptionRepository, CreditRepository,
    ProductRepository, CategoryRepository, PlatformRepository, WatchlistRepository, AlertRepository,
    NotificationRepository, ReportRepository, DataSourceRepository, SettingsRepository,
    MarketplaceProductRepository, ShopifyRepository, UnifiedProductRepository, LLMUsageRepository,
    DataQualityRepository, TaxonomyRepository, ScraperRepository, MarketIntelligenceRepository
)
from backend.app.db.models import (
    UserModel, WorkspaceModel, WorkspaceMemberModel, UserSessionModel, EmailVerificationModel,
    PasswordResetTokenModel, LoginEventModel, UserSettingsModel, ProductModel, CategoryModel,
    PlatformModel, WatchlistModel, AlertModel, NotificationModel, ReportModel, DataSourceModel, SettingsModel,
    SubscriptionPlanModel, UserSubscriptionModel, CreditAccountModel, CreditTransactionModel, CreditUsageModel,
    MarketplaceProductModel, ProductMarketSnapshotModel,
    DarazSellerModel, DarazCategoryModel, DarazReviewModel, DarazIngestionRunModel, DarazApiTelemetryModel, DarazDailyQuotaModel, DarazTrainingDatasetModel,
    ShopifyProductModel, ShopifyProductSnapshotModel, ShopifyProviderHealthModel, ShopifySyncRunModel,
    UnifiedProductModel, ProductPlatformListingModel, ProductMatchCandidateModel, ProductMatchAuditModel, ProductMatchDecisionModel,
    LLMUsageRecordModel, AIAgentModel, AIAgentRunModel, AIAgentMemoryModel, AIAgentMemoryEventModel,
    DataQualityValidationResultModel, TaxonomyCategoryModel, ProductTaxonomyAssignmentModel, ProductTaxonomyCandidateModel,
    ScraperCrawlJobModel, RawScrapedPayloadModel,
    MarketIntelligenceSnapshotModel, SocialSignalModel
)




class PostgresUserRepository(UserRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _to_domain(self, m: UserModel) -> User:
        return User(
            id=m.id,
            email=m.email,
            hashed_password=m.hashed_password,
            full_name=m.full_name,
            is_active=m.is_active,
            is_verified=m.is_verified,
            role=m.role,
            verification_token=m.verification_token,
            reset_token=m.reset_token,
            reset_token_expires_at=m.reset_token_expires_at,
            workspace_id=m.workspace_id,
            avatar_url=m.avatar_url,
            last_login_at=m.last_login_at,
            created_at=m.created_at
        )

    def get_by_id(self, user_id: str) -> Optional[User]:
        if not self.session:
            return None
        m = self.session.query(UserModel).filter(UserModel.id == user_id).first()
        return self._to_domain(m) if m else None

    def get_by_email(self, email: str) -> Optional[User]:
        if not self.session:
            return None
        m = self.session.query(UserModel).filter(UserModel.email.ilike(email.strip())).first()
        return self._to_domain(m) if m else None

    def get_by_verification_token(self, token: str) -> Optional[User]:
        if not self.session:
            return None
        m = self.session.query(UserModel).filter(UserModel.verification_token == token).first()
        return self._to_domain(m) if m else None

    def get_by_reset_token(self, token: str) -> Optional[User]:
        if not self.session:
            return None
        m = self.session.query(UserModel).filter(UserModel.reset_token == token).first()
        return self._to_domain(m) if m else None

    def create(self, user: User) -> User:
        if not self.session:
            return user
        m = UserModel(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            role=user.role,
            verification_token=user.verification_token,
            reset_token=user.reset_token,
            reset_token_expires_at=user.reset_token_expires_at,
            workspace_id=user.workspace_id,
            avatar_url=user.avatar_url,
            last_login_at=user.last_login_at,
            created_at=user.created_at
        )
        self.session.add(m)
        self.session.commit()
        return user

    def update(self, user: User) -> User:
        if not self.session:
            return user
        m = self.session.query(UserModel).filter(UserModel.id == user.id).first()
        if m:
            m.email = user.email
            m.hashed_password = user.hashed_password
            m.full_name = user.full_name
            m.is_active = user.is_active
            m.is_verified = user.is_verified
            m.role = user.role
            m.verification_token = user.verification_token
            m.reset_token = user.reset_token
            m.reset_token_expires_at = user.reset_token_expires_at
            m.workspace_id = user.workspace_id
            m.avatar_url = user.avatar_url
            m.last_login_at = user.last_login_at
            self.session.commit()
        return user

    def delete(self, user_id: str) -> bool:
        if not self.session:
            return False
        count = self.session.query(UserModel).filter(UserModel.id == user_id).delete()
        self.session.commit()
        return count > 0

class PostgresWorkspaceRepository(WorkspaceRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _to_domain(self, m: WorkspaceModel) -> Workspace:
        return Workspace(
            id=m.id,
            name=m.name,
            industry=m.industry,
            use_case=m.use_case,
            currency=m.currency,
            default_dashboard=m.default_dashboard,
            connected_sources=m.connected_sources or [],
            is_setup_complete=m.is_setup_complete,
            owner_id=m.owner_id,
            created_at=m.created_at
        )

    def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        if not self.session:
            return None
        m = self.session.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
        return self._to_domain(m) if m else None

    def get_by_owner_id(self, owner_id: str) -> Optional[Workspace]:
        if not self.session:
            return None
        m = self.session.query(WorkspaceModel).filter(WorkspaceModel.owner_id == owner_id).first()
        return self._to_domain(m) if m else None

    def create(self, workspace: Workspace) -> Workspace:
        if not self.session:
            return workspace
        m = WorkspaceModel(
            id=workspace.id,
            name=workspace.name,
            industry=workspace.industry,
            use_case=workspace.use_case,
            currency=workspace.currency,
            default_dashboard=workspace.default_dashboard,
            connected_sources=workspace.connected_sources,
            is_setup_complete=workspace.is_setup_complete,
            owner_id=workspace.owner_id,
            created_at=workspace.created_at
        )
        self.session.add(m)
        self.session.commit()
        return workspace

    def update(self, workspace: Workspace) -> Workspace:
        if not self.session:
            return workspace
        m = self.session.query(WorkspaceModel).filter(WorkspaceModel.id == workspace.id).first()
        if m:
            m.name = workspace.name
            m.industry = workspace.industry
            m.use_case = workspace.use_case
            m.currency = workspace.currency
            m.default_dashboard = workspace.default_dashboard
            m.connected_sources = workspace.connected_sources
            m.is_setup_complete = workspace.is_setup_complete
            self.session.commit()
        return workspace

    def add_member(self, member: WorkspaceMember) -> WorkspaceMember:
        if not self.session:
            return member
        m = WorkspaceMemberModel(
            id=member.id,
            workspace_id=member.workspace_id,
            user_id=member.user_id,
            role=member.role,
            created_at=member.created_at
        )
        self.session.add(m)
        self.session.commit()
        return member

    def get_members(self, workspace_id: str) -> List[WorkspaceMember]:
        if not self.session:
            return []
        rows = self.session.query(WorkspaceMemberModel).filter(WorkspaceMemberModel.workspace_id == workspace_id).all()
        return [
            WorkspaceMember(
                id=r.id,
                workspace_id=r.workspace_id,
                user_id=r.user_id,
                role=r.role,
                created_at=r.created_at
            ) for r in rows
        ]

    def delete(self, workspace_id: str) -> bool:
        if not self.session:
            return False
        self.session.query(WorkspaceMemberModel).filter(WorkspaceMemberModel.workspace_id == workspace_id).delete()
        count = self.session.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).delete()
        self.session.commit()
        return count > 0

class PostgresAuthPersistenceRepository(AuthPersistenceRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def create_session(self, session: UserSession) -> UserSession:
        if not self.session:
            return session
        m = UserSessionModel(
            id=session.id,
            user_id=session.user_id,
            token_hash=session.token_hash,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            is_revoked=session.is_revoked,
            expires_at=session.expires_at,
            created_at=session.created_at
        )
        self.session.add(m)
        self.session.commit()
        return session

    def get_session(self, token_hash: str) -> Optional[UserSession]:
        if not self.session:
            return None
        m = self.session.query(UserSessionModel).filter(UserSessionModel.token_hash == token_hash).first()
        if not m:
            return None
        return UserSession(
            id=m.id,
            user_id=m.user_id,
            token_hash=m.token_hash,
            ip_address=m.ip_address,
            user_agent=m.user_agent,
            is_revoked=m.is_revoked,
            expires_at=m.expires_at,
            created_at=m.created_at
        )

    def revoke_session(self, token_hash: str) -> bool:
        if not self.session:
            return False
        m = self.session.query(UserSessionModel).filter(UserSessionModel.token_hash == token_hash).first()
        if m:
            m.is_revoked = True
            self.session.commit()
            return True
        return False

    def revoke_all_user_sessions(self, user_id: str) -> int:
        if not self.session:
            return 0
        count = self.session.query(UserSessionModel).filter(
            UserSessionModel.user_id == user_id, UserSessionModel.is_revoked == False
        ).update({"is_revoked": True})
        self.session.commit()
        return count

    def create_email_verification(self, verification: EmailVerification) -> EmailVerification:
        if not self.session:
            return verification
        m = EmailVerificationModel(
            id=verification.id,
            user_id=verification.user_id,
            token=verification.token,
            expires_at=verification.expires_at,
            used_at=verification.used_at,
            created_at=verification.created_at
        )
        self.session.add(m)
        self.session.commit()
        return verification

    def get_email_verification(self, token: str) -> Optional[EmailVerification]:
        if not self.session:
            return None
        m = self.session.query(EmailVerificationModel).filter(EmailVerificationModel.token == token).first()
        if not m:
            return None
        return EmailVerification(
            id=m.id,
            user_id=m.user_id,
            token=m.token,
            expires_at=m.expires_at,
            used_at=m.used_at,
            created_at=m.created_at
        )

    def mark_email_verification_used(self, token: str) -> bool:
        if not self.session:
            return False
        m = self.session.query(EmailVerificationModel).filter(EmailVerificationModel.token == token).first()
        if m:
            m.used_at = datetime.now(timezone.utc)
            self.session.commit()
            return True
        return False

    def invalidate_user_verifications(self, user_id: str) -> int:
        if not self.session:
            return 0
        now = datetime.now(timezone.utc)
        count = self.session.query(EmailVerificationModel).filter(
            EmailVerificationModel.user_id == user_id,
            EmailVerificationModel.used_at == None
        ).update({"used_at": now})
        self.session.commit()
        return count

    def create_password_reset_token(self, reset_token: PasswordResetToken) -> PasswordResetToken:
        if not self.session:
            return reset_token
        m = PasswordResetTokenModel(
            id=reset_token.id,
            user_id=reset_token.user_id,
            token=reset_token.token,
            expires_at=reset_token.expires_at,
            used_at=reset_token.used_at,
            created_at=reset_token.created_at
        )
        self.session.add(m)
        self.session.commit()
        return reset_token

    def get_password_reset_token(self, token: str) -> Optional[PasswordResetToken]:
        if not self.session:
            return None
        m = self.session.query(PasswordResetTokenModel).filter(PasswordResetTokenModel.token == token).first()
        if not m:
            return None
        return PasswordResetToken(
            id=m.id,
            user_id=m.user_id,
            token=m.token,
            expires_at=m.expires_at,
            used_at=m.used_at,
            created_at=m.created_at
        )

    def mark_password_reset_token_used(self, token: str) -> bool:
        if not self.session:
            return False
        m = self.session.query(PasswordResetTokenModel).filter(PasswordResetTokenModel.token == token).first()
        if m:
            m.used_at = datetime.now(timezone.utc)
            self.session.commit()
            return True
        return False

    def record_login_event(self, event: LoginEvent) -> LoginEvent:
        if not self.session:
            return event
        m = LoginEventModel(
            id=event.id,
            user_id=event.user_id,
            email=event.email,
            event_type=event.event_type,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            metadata_json=event.metadata_json or {},
            created_at=event.created_at
        )
        self.session.add(m)
        self.session.commit()
        return event

    def list_login_events(self, user_id: Optional[str] = None, email: Optional[str] = None) -> List[LoginEvent]:
        if not self.session:
            return []
        q = self.session.query(LoginEventModel)
        if user_id:
            q = q.filter(LoginEventModel.user_id == user_id)
        if email:
            q = q.filter(LoginEventModel.email.ilike(email.strip()))
        rows = q.order_by(LoginEventModel.created_at.desc()).all()
        return [
            LoginEvent(
                id=r.id,
                user_id=r.user_id,
                email=r.email,
                event_type=r.event_type,
                ip_address=r.ip_address,
                user_agent=r.user_agent,
                metadata_json=r.metadata_json or {},
                created_at=r.created_at
            ) for r in rows
        ]

class PostgresProductRepository(ProductRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _to_domain(self, m: ProductModel) -> Product:
        return Product(
            id=m.id,
            name=m.name,
            category=m.category,
            sub_category=m.sub_category,
            trend_score=m.trend_score,
            growth_rate=m.growth_rate,
            volume=m.volume,
            velocity_label=m.velocity_label,
            status=m.status,
            price_range=m.price_range,
            primary_platform=m.primary_platform,
            platforms=m.platforms or [],
            platform_shares=m.platform_shares or {},
            historical_scores=m.historical_scores or [],
            historical_prices=m.historical_prices or [],
            ai_summary=m.ai_summary or "",
            signals_count=m.signals_count,
            sentiment_score=m.sentiment_score,
            image_url=m.image_url,
            tags=m.tags or [],
            is_watchlisted=m.is_watchlisted,
            raw_data=m.raw_data or {},
            created_at=m.created_at
        )

    def get_by_id(self, product_id: str) -> Optional[Product]:
        if not self.session:
            return None
        m = self.session.query(ProductModel).filter(ProductModel.id == product_id).first()
        return self._to_domain(m) if m else None

    def list(
        self,
        category: Optional[str] = None,
        platform: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None
    ) -> List[Product]:
        if not self.session:
            return []
        query = self.session.query(ProductModel)
        if category and category.lower() != "all":
            query = query.filter(ProductModel.category.ilike(category))
        if platform and platform.lower() != "all":
            query = query.filter(ProductModel.primary_platform.ilike(platform))
        if search:
            s = f"%{search.strip()}%"
            query = query.filter(ProductModel.name.ilike(s) | ProductModel.category.ilike(s))

        if sort_by == "growth_rate":
            query = query.order_by(ProductModel.growth_rate.desc())
        elif sort_by == "volume":
            query = query.order_by(ProductModel.volume.desc())
        else:
            query = query.order_by(ProductModel.trend_score.desc())

        results = query.all()
        return [self._to_domain(m) for m in results]

    def update(self, product: Product) -> Product:
        if not self.session:
            return product
        m = self.session.query(ProductModel).filter(ProductModel.id == product.id).first()
        if m:
            m.name = product.name
            m.category = product.category
            m.sub_category = product.sub_category
            m.trend_score = product.trend_score
            m.growth_rate = product.growth_rate
            m.volume = product.volume
            m.velocity_label = product.velocity_label
            m.status = product.status
            m.price_range = product.price_range
            m.primary_platform = product.primary_platform
            m.platforms = product.platforms
            m.platform_shares = product.platform_shares
            m.historical_scores = product.historical_scores
            m.historical_prices = product.historical_prices
            m.ai_summary = product.ai_summary
            m.signals_count = product.signals_count
            m.sentiment_score = product.sentiment_score
            m.image_url = product.image_url
            m.tags = product.tags
            m.is_watchlisted = product.is_watchlisted
            m.raw_data = product.raw_data or {}
            self.session.commit()
        return product

class PostgresCategoryRepository(CategoryRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _to_domain(self, m: CategoryModel) -> Category:
        return Category(
            id=m.id,
            name=m.name,
            slug=m.slug,
            product_count=m.product_count,
            avg_trend_score=m.avg_trend_score,
            growth_rate=m.growth_rate,
            velocity_label=m.velocity_label,
            subcategories=m.subcategories or [],
            top_driver=m.top_driver or "",
            created_at=m.created_at
        )

    def list(self) -> List[Category]:
        if not self.session:
            return []
        items = self.session.query(CategoryModel).order_by(CategoryModel.avg_trend_score.desc()).all()
        return [self._to_domain(m) for m in items]

    def get_by_id(self, category_id: str) -> Optional[Category]:
        if not self.session:
            return None
        m = self.session.query(CategoryModel).filter(CategoryModel.id == category_id).first()
        return self._to_domain(m) if m else None

class PostgresPlatformRepository(PlatformRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _to_domain(self, m: PlatformModel) -> PlatformMetrics:
        return PlatformMetrics(
            id=m.id,
            name=m.name,
            slug=m.slug,
            icon=m.icon,
            total_signals=m.total_signals,
            active_trends=m.active_trends,
            velocity_growth=m.velocity_growth,
            market_share=m.market_share,
            status=m.status,
            recent_spikes=m.recent_spikes or [],
            created_at=m.created_at
        )

    def list(self) -> List[PlatformMetrics]:
        if not self.session:
            return []
        items = self.session.query(PlatformModel).order_by(PlatformModel.market_share.desc()).all()
        return [self._to_domain(m) for m in items]

    def get_by_slug(self, slug: str) -> Optional[PlatformMetrics]:
        if not self.session:
            return None
        m = self.session.query(PlatformModel).filter(PlatformModel.slug == slug).first()
        return self._to_domain(m) if m else None

class PostgresWatchlistRepository(WatchlistRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def list_product_ids(self, user_id: str) -> List[str]:
        if not self.session:
            return []
        rows = self.session.query(WatchlistModel.product_id).filter(WatchlistModel.user_id == user_id).all()
        return [r[0] for r in rows]

    def add(self, user_id: str, product_id: str) -> bool:
        if not self.session:
            return True
        existing = self.session.query(WatchlistModel).filter(
            WatchlistModel.user_id == user_id, WatchlistModel.product_id == product_id
        ).first()
        if not existing:
            m = WatchlistModel(id=f"w_{uuid.uuid4().hex[:8]}", user_id=user_id, product_id=product_id)
            self.session.add(m)
            self.session.commit()
        return True

    def remove(self, user_id: str, product_id: str) -> bool:
        if not self.session:
            return True
        self.session.query(WatchlistModel).filter(
            WatchlistModel.user_id == user_id, WatchlistModel.product_id == product_id
        ).delete()
        self.session.commit()
        return True

    def is_in_watchlist(self, user_id: str, product_id: str) -> bool:
        if not self.session:
            return False
        count = self.session.query(WatchlistModel).filter(
            WatchlistModel.user_id == user_id, WatchlistModel.product_id == product_id
        ).count()
        return count > 0

class PostgresAlertRepository(AlertRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _to_domain(self, m: AlertModel) -> Alert:
        return Alert(
            id=m.id,
            title=m.title,
            description=m.description,
            severity=m.severity,
            category=m.category,
            product_id=m.product_id,
            product_name=m.product_name,
            platform=m.platform,
            trigger=m.trigger,
            threshold=m.threshold,
            actual_value=m.actual_value,
            is_read=m.is_read,
            is_resolved=m.is_resolved,
            created_at=m.created_at
        )

    def list(self, severity: Optional[str] = None, unread_only: bool = False) -> List[Alert]:
        if not self.session:
            return []
        query = self.session.query(AlertModel)
        if severity and severity.lower() != "all":
            query = query.filter(AlertModel.severity.ilike(severity))
        if unread_only:
            query = query.filter(AlertModel.is_read == False)
        items = query.order_by(AlertModel.created_at.desc()).all()
        return [self._to_domain(m) for m in items]

    def get_by_id(self, alert_id: str) -> Optional[Alert]:
        if not self.session:
            return None
        m = self.session.query(AlertModel).filter(AlertModel.id == alert_id).first()
        return self._to_domain(m) if m else None

    def create(self, alert: Alert) -> Alert:
        if not self.session:
            return alert
        m = AlertModel(
            id=alert.id,
            title=alert.title,
            description=alert.description,
            severity=alert.severity,
            category=alert.category,
            product_id=alert.product_id,
            product_name=alert.product_name,
            platform=alert.platform,
            trigger=alert.trigger,
            threshold=alert.threshold,
            actual_value=alert.actual_value,
            is_read=alert.is_read,
            is_resolved=alert.is_resolved,
            created_at=alert.created_at
        )
        self.session.add(m)
        self.session.commit()
        return alert

    def mark_read(self, alert_id: str) -> Optional[Alert]:
        if not self.session:
            return None
        m = self.session.query(AlertModel).filter(AlertModel.id == alert_id).first()
        if m:
            m.is_read = True
            self.session.commit()
            return self._to_domain(m)
        return None

    def resolve(self, alert_id: str) -> Optional[Alert]:
        if not self.session:
            return None
        m = self.session.query(AlertModel).filter(AlertModel.id == alert_id).first()
        if m:
            m.is_resolved = True
            m.is_read = True
            self.session.commit()
            return self._to_domain(m)
        return None

class PostgresNotificationRepository(NotificationRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _to_domain(self, m: NotificationModel) -> Notification:
        return Notification(
            id=m.id,
            title=m.title,
            message=m.message,
            type=m.type,
            is_read=m.is_read,
            link=m.link,
            created_at=m.created_at
        )

    def list(self, unread_only: bool = False) -> List[Notification]:
        if not self.session:
            return []
        query = self.session.query(NotificationModel)
        if unread_only:
            query = query.filter(NotificationModel.is_read == False)
        items = query.order_by(NotificationModel.created_at.desc()).all()
        return [self._to_domain(m) for m in items]

    def mark_read(self, notification_id: str) -> Optional[Notification]:
        if not self.session:
            return None
        m = self.session.query(NotificationModel).filter(NotificationModel.id == notification_id).first()
        if m:
            m.is_read = True
            self.session.commit()
            return self._to_domain(m)
        return None

    def mark_all_read(self) -> int:
        if not self.session:
            return 0
        count = self.session.query(NotificationModel).filter(NotificationModel.is_read == False).update({"is_read": True})
        self.session.commit()
        return count

class PostgresReportRepository(ReportRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _to_domain(self, m: ReportModel) -> Report:
        snap = m.data_snapshot or {}
        return Report(
            id=m.id,
            title=m.title,
            template=m.template,
            time_range=m.time_range,
            status=m.status,
            category=m.category_focus or snap.get("category", "All Categories"),
            platforms=snap.get("platforms", []),
            key_findings=snap.get("key_findings", []),
            ai_takeaways=snap.get("ai_takeaways", ""),
            total_signals_analyzed=snap.get("total_signals_analyzed", 0),
            high_conviction_count=snap.get("high_conviction_count", 0),
            products_evaluated=snap.get("products_evaluated", 0),
            provenance=snap.get("provenance", "persisted_observations"),
            data_sufficiency=snap.get("data_sufficiency", "insufficient_data"),
            observation_count=snap.get("observation_count", 0),
            historical_observation_count=snap.get("historical_observation_count", 0),
            source_breakdown=snap.get("source_breakdown", {}),
            pdf_url=m.download_url or snap.get("pdf_url"),
            csv_url=snap.get("csv_url", f"/api/v1/reports/{m.id}/export?format=csv"),
            created_by=snap.get("created_by", "Admin"),
            created_at=m.created_at
        )

    def list(self) -> List[Report]:
        if not self.session:
            return []
        items = self.session.query(ReportModel).order_by(ReportModel.created_at.desc()).all()
        return [self._to_domain(m) for m in items]

    def get_by_id(self, report_id: str) -> Optional[Report]:
        if not self.session:
            return None
        m = self.session.query(ReportModel).filter(ReportModel.id == report_id).first()
        return self._to_domain(m) if m else None

    def create(self, report: Report) -> Report:
        if not self.session:
            return report
        snap = {
            "category": report.category,
            "platforms": report.platforms,
            "key_findings": report.key_findings,
            "ai_takeaways": report.ai_takeaways,
            "total_signals_analyzed": report.total_signals_analyzed,
            "high_conviction_count": report.high_conviction_count,
            "products_evaluated": report.products_evaluated,
            "provenance": report.provenance,
            "data_sufficiency": report.data_sufficiency,
            "observation_count": report.observation_count,
            "historical_observation_count": report.historical_observation_count,
            "source_breakdown": report.source_breakdown,
            "pdf_url": report.pdf_url,
            "csv_url": report.csv_url,
            "created_by": report.created_by,
        }
        m = ReportModel(
            id=report.id,
            title=report.title,
            template=report.template,
            time_range=report.time_range,
            status=report.status,
            download_url=report.pdf_url,
            file_size="1.2 MB",
            category_focus=report.category or "All Categories",
            data_snapshot=snap,
            created_at=report.created_at
        )
        self.session.add(m)
        self.session.commit()
        return report

    def update(self, report: Report) -> Report:
        if not self.session:
            return report
        m = self.session.query(ReportModel).filter(ReportModel.id == report.id).first()
        if m:
            m.title = report.title
            m.status = report.status
            m.download_url = report.pdf_url
            m.data_snapshot = {
                "category": report.category,
                "platforms": report.platforms,
                "key_findings": report.key_findings,
                "ai_takeaways": report.ai_takeaways,
                "total_signals_analyzed": report.total_signals_analyzed,
                "high_conviction_count": report.high_conviction_count,
                "products_evaluated": report.products_evaluated,
                "provenance": report.provenance,
                "data_sufficiency": report.data_sufficiency,
                "observation_count": report.observation_count,
                "historical_observation_count": report.historical_observation_count,
                "source_breakdown": report.source_breakdown,
                "pdf_url": report.pdf_url,
                "csv_url": report.csv_url,
                "created_by": report.created_by,
            }
            self.session.commit()
        return report

class PostgresDataSourceRepository(DataSourceRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _to_domain(self, m: DataSourceModel) -> DataSource:
        return DataSource(
            id=m.id,
            name=m.name,
            slug=m.slug,
            status=m.status,
            health_score=m.health_score,
            records_synced=m.records_synced,
            last_sync=m.last_sync,
            error_count=m.error_count,
            icon=m.icon,
            created_at=m.created_at
        )

    def list(self) -> List[DataSource]:
        if not self.session:
            return []
        items = self.session.query(DataSourceModel).all()
        return [self._to_domain(m) for m in items]

    def get_by_slug(self, slug: str) -> Optional[DataSource]:
        if not self.session:
            return None
        m = self.session.query(DataSourceModel).filter(DataSourceModel.slug == slug).first()
        return self._to_domain(m) if m else None

    def update_status(self, slug: str, status: str) -> Optional[DataSource]:
        if not self.session:
            return None
        m = self.session.query(DataSourceModel).filter(DataSourceModel.slug == slug).first()
        if m:
            m.status = status
            self.session.commit()
            return self._to_domain(m)
        return None

    def update(self, data_source: DataSource) -> DataSource:
        if not self.session:
            return data_source
        m = self.session.query(DataSourceModel).filter(DataSourceModel.slug == data_source.slug).first()
        if m:
            m.name = data_source.name
            m.status = data_source.status
            m.health_score = data_source.health_score
            m.records_synced = data_source.records_synced
            m.last_sync = data_source.last_sync
            m.error_count = data_source.error_count
            m.icon = data_source.icon
            self.session.commit()
        return data_source

class PostgresSettingsRepository(SettingsRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _to_domain(self, m: UserSettingsModel) -> UserSettings:
        return UserSettings(
            user_id=m.user_id,
            full_name=m.full_name,
            email=m.email,
            avatar_url=m.avatar_url,
            role=m.role,
            company_name=m.company_name,
            timezone=m.timezone,
            currency=m.currency,
            email_notifications=m.email_notifications,
            alert_critical_only=m.alert_critical_only,
            weekly_digest=m.weekly_digest,
            ai_model_preference=m.ai_model_preference,
            ai_confidence_threshold=m.ai_confidence_threshold,
            auto_generate_reports=m.auto_generate_reports,
            dark_mode=m.dark_mode,
            table_dense_view=m.table_dense_view,
            live_ticker_enabled=m.live_ticker_enabled
        )

    def get_by_user_id(self, user_id: str) -> Optional[UserSettings]:
        if not self.session:
            return None
        m = self.session.query(UserSettingsModel).filter(UserSettingsModel.user_id == user_id).first()
        return self._to_domain(m) if m else None

    def update(self, settings: UserSettings) -> UserSettings:
        if not self.session:
            return settings
        m = self.session.query(UserSettingsModel).filter(UserSettingsModel.user_id == settings.user_id).first()
        if m:
            m.full_name = settings.full_name
            m.email = settings.email
            m.avatar_url = settings.avatar_url
            m.role = settings.role
            m.company_name = settings.company_name
            m.timezone = settings.timezone
            m.currency = settings.currency
            m.email_notifications = settings.email_notifications
            m.alert_critical_only = settings.alert_critical_only
            m.weekly_digest = settings.weekly_digest
            m.ai_model_preference = settings.ai_model_preference
            m.ai_confidence_threshold = settings.ai_confidence_threshold
            m.auto_generate_reports = settings.auto_generate_reports
            m.dark_mode = settings.dark_mode
            m.table_dense_view = settings.table_dense_view
            m.live_ticker_enabled = settings.live_ticker_enabled
            m.updated_at = datetime.now(timezone.utc)
        else:
            m = UserSettingsModel(
                id=f"st_{uuid.uuid4().hex[:8]}",
                user_id=settings.user_id,
                full_name=settings.full_name,
                email=settings.email,
                avatar_url=settings.avatar_url,
                role=settings.role,
                company_name=settings.company_name,
                timezone=settings.timezone,
                currency=settings.currency,
                email_notifications=settings.email_notifications,
                alert_critical_only=settings.alert_critical_only,
                weekly_digest=settings.weekly_digest,
                ai_model_preference=settings.ai_model_preference,
                ai_confidence_threshold=settings.ai_confidence_threshold,
                auto_generate_reports=settings.auto_generate_reports,
                dark_mode=settings.dark_mode,
                table_dense_view=settings.table_dense_view,
                live_ticker_enabled=settings.live_ticker_enabled
            )
            self.session.add(m)
        self.session.commit()
        return settings

class PostgresSubscriptionRepository(SubscriptionRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _plan_to_domain(self, m: SubscriptionPlanModel) -> SubscriptionPlan:
        return SubscriptionPlan(
            id=m.id,
            name=m.name,
            slug=m.slug,
            description=m.description,
            price=m.price,
            currency=m.currency,
            billing_interval=m.billing_interval,
            monthly_credits=m.monthly_credits,
            is_active=m.is_active,
            features=m.features or [],
            limits=m.limits or {},
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def _sub_to_domain(self, m: UserSubscriptionModel) -> UserSubscription:
        return UserSubscription(
            id=m.id,
            user_id=m.user_id,
            plan_id=m.plan_id,
            status=m.status,
            started_at=m.started_at,
            current_period_start=m.current_period_start,
            current_period_end=m.current_period_end,
            cancelled_at=m.cancelled_at,
            metadata_json=m.metadata_json or {},
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def list_plans(self, active_only: bool = True) -> List[SubscriptionPlan]:
        if not self.session:
            return []
        query = self.session.query(SubscriptionPlanModel)
        if active_only:
            query = query.filter(SubscriptionPlanModel.is_active.is_(True))
        models = query.all()
        return [self._plan_to_domain(m) for m in models]

    def get_plan_by_id(self, plan_id: str) -> Optional[SubscriptionPlan]:
        if not self.session:
            return None
        m = self.session.query(SubscriptionPlanModel).filter(SubscriptionPlanModel.id == plan_id).first()
        return self._plan_to_domain(m) if m else None

    def get_plan_by_slug(self, slug: str) -> Optional[SubscriptionPlan]:
        if not self.session:
            return None
        m = self.session.query(SubscriptionPlanModel).filter(SubscriptionPlanModel.slug.ilike(slug.strip())).first()
        return self._plan_to_domain(m) if m else None

    def get_user_subscription(self, user_id: str) -> Optional[UserSubscription]:
        if not self.session:
            return None
        m = self.session.query(UserSubscriptionModel).filter(UserSubscriptionModel.user_id == user_id).first()
        return self._sub_to_domain(m) if m else None

    def create_user_subscription(self, subscription: UserSubscription) -> UserSubscription:
        if not self.session:
            return subscription
        m = UserSubscriptionModel(
            id=subscription.id,
            user_id=subscription.user_id,
            plan_id=subscription.plan_id,
            status=subscription.status,
            started_at=subscription.started_at,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancelled_at=subscription.cancelled_at,
            metadata_json=subscription.metadata_json,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at
        )
        self.session.add(m)
        self.session.commit()
        return subscription

    def update_user_subscription(self, subscription: UserSubscription) -> UserSubscription:
        if not self.session:
            return subscription
        m = self.session.query(UserSubscriptionModel).filter(UserSubscriptionModel.user_id == subscription.user_id).first()
        if m:
            m.plan_id = subscription.plan_id
            m.status = subscription.status
            m.current_period_start = subscription.current_period_start
            m.current_period_end = subscription.current_period_end
            m.cancelled_at = subscription.cancelled_at
            m.metadata_json = subscription.metadata_json
            m.updated_at = datetime.now(timezone.utc)
            self.session.commit()
        return subscription

class PostgresCreditRepository(CreditRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _account_to_domain(self, m: CreditAccountModel) -> CreditAccount:
        return CreditAccount(
            id=m.id,
            user_id=m.user_id,
            current_balance=m.current_balance,
            lifetime_granted=m.lifetime_granted,
            lifetime_used=m.lifetime_used,
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def _tx_to_domain(self, m: CreditTransactionModel) -> CreditTransaction:
        return CreditTransaction(
            id=m.id,
            credit_account_id=m.credit_account_id,
            user_id=m.user_id,
            amount=m.amount,
            transaction_type=m.transaction_type,
            balance_before=m.balance_before,
            balance_after=m.balance_after,
            reference_type=m.reference_type,
            reference_id=m.reference_id,
            description=m.description,
            metadata_json=m.metadata_json or {},
            created_at=m.created_at
        )

    def _usage_to_domain(self, m: CreditUsageModel) -> CreditUsage:
        return CreditUsage(
            id=m.id,
            user_id=m.user_id,
            credit_account_id=m.credit_account_id,
            feature=m.feature,
            action=m.action,
            credits_used=m.credits_used,
            reference_type=m.reference_type,
            reference_id=m.reference_id,
            metadata_json=m.metadata_json or {},
            created_at=m.created_at
        )

    def get_or_create_account(self, user_id: str) -> CreditAccount:
        if not self.session:
            return CreditAccount(
                id=f"cacc_{user_id.replace('usr_', '')}",
                user_id=user_id,
                current_balance=0
            )
        m = self.session.query(CreditAccountModel).filter(CreditAccountModel.user_id == user_id).first()
        if not m:
            now = datetime.now(timezone.utc)
            m = CreditAccountModel(
                id=f"cacc_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                current_balance=0,
                lifetime_granted=0,
                lifetime_used=0,
                created_at=now,
                updated_at=now
            )
            self.session.add(m)
            self.session.commit()
        return self._account_to_domain(m)

    def get_account(self, user_id: str) -> Optional[CreditAccount]:
        if not self.session:
            return None
        m = self.session.query(CreditAccountModel).filter(CreditAccountModel.user_id == user_id).first()
        return self._account_to_domain(m) if m else None

    def update_account_balance(self, user_id: str, new_balance: int, delta_granted: int, delta_used: int) -> CreditAccount:
        if not self.session:
            return CreditAccount(id="mock", user_id=user_id, current_balance=new_balance)
        if new_balance < 0:
            raise ValueError("Credit balance cannot become negative")
        m = self.session.query(CreditAccountModel).filter(CreditAccountModel.user_id == user_id).with_for_update().first()
        if not m:
            now = datetime.now(timezone.utc)
            m = CreditAccountModel(
                id=f"cacc_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                current_balance=new_balance,
                lifetime_granted=delta_granted,
                lifetime_used=delta_used,
                created_at=now,
                updated_at=now
            )
            self.session.add(m)
        else:
            m.current_balance = new_balance
            m.lifetime_granted += delta_granted
            m.lifetime_used += delta_used
            m.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        return self._account_to_domain(m)

    def create_transaction(self, tx: CreditTransaction) -> CreditTransaction:
        if not self.session:
            return tx
        m = CreditTransactionModel(
            id=tx.id,
            credit_account_id=tx.credit_account_id,
            user_id=tx.user_id,
            amount=tx.amount,
            transaction_type=tx.transaction_type,
            balance_before=tx.balance_before,
            balance_after=tx.balance_after,
            reference_type=tx.reference_type,
            reference_id=tx.reference_id,
            description=tx.description,
            metadata_json=tx.metadata_json,
            created_at=tx.created_at
        )
        self.session.add(m)
        self.session.commit()
        return tx

    def get_transaction_by_reference(self, user_id: str, reference_type: str, reference_id: str) -> Optional[CreditTransaction]:
        if not self.session:
            return None
        m = self.session.query(CreditTransactionModel).filter(
            CreditTransactionModel.user_id == user_id,
            CreditTransactionModel.reference_type == reference_type,
            CreditTransactionModel.reference_id == reference_id
        ).order_by(CreditTransactionModel.created_at.desc()).first()
        return self._tx_to_domain(m) if m else None

    def list_transactions(self, user_id: str, limit: int = 50, offset: int = 0) -> List[CreditTransaction]:
        if not self.session:
            return []
        models = self.session.query(CreditTransactionModel).filter(
            CreditTransactionModel.user_id == user_id
        ).order_by(CreditTransactionModel.created_at.desc()).offset(offset).limit(limit).all()
        return [self._tx_to_domain(m) for m in models]

    def record_usage(self, usage: CreditUsage) -> CreditUsage:
        if not self.session:
            return usage
        m = CreditUsageModel(
            id=usage.id,
            user_id=usage.user_id,
            credit_account_id=usage.credit_account_id,
            feature=usage.feature,
            action=usage.action,
            credits_used=usage.credits_used,
            reference_type=usage.reference_type,
            reference_id=usage.reference_id,
            metadata_json=usage.metadata_json,
            created_at=usage.created_at
        )
        self.session.add(m)
        self.session.commit()
        return usage

    def get_usage_by_reference(self, user_id: str, reference_type: str, reference_id: str) -> Optional[CreditUsage]:
        if not self.session:
            return None
        m = self.session.query(CreditUsageModel).filter(
            CreditUsageModel.user_id == user_id,
            CreditUsageModel.reference_type == reference_type,
            CreditUsageModel.reference_id == reference_id
        ).order_by(CreditUsageModel.created_at.desc()).first()
        return self._usage_to_domain(m) if m else None

    def list_usage(self, user_id: str, limit: int = 50, offset: int = 0) -> List[CreditUsage]:
        if not self.session:
            return []
        models = self.session.query(CreditUsageModel).filter(
            CreditUsageModel.user_id == user_id
        ).order_by(CreditUsageModel.created_at.desc()).offset(offset).limit(limit).all()
        return [self._usage_to_domain(m) for m in models]

class PostgresMarketplaceProductRepository(MarketplaceProductRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _prod_to_domain(self, m: MarketplaceProductModel) -> MarketplaceProduct:
        return MarketplaceProduct(
            id=m.id,
            platform=m.platform,
            product_id=m.product_id,
            product_name=m.product_name,
            product_url=m.product_url,
            image_url=m.image_url,
            seller_name=m.seller_name,
            seller_id=m.seller_id,
            category=m.category,
            price=m.price or 0.0,
            original_price=m.original_price or 0.0,
            discount_percentage=m.discount_percentage or 0.0,
            discount_label=m.discount_label,
            rating=m.rating or 0.0,
            review_count=m.review_count or 0,
            stock_status=m.stock_status or "in_stock",
            in_stock=m.in_stock if m.in_stock is not None else True,
            currency=m.currency or "PKR",
            location=m.location,
            first_seen_at=m.first_seen_at or m.created_at,
            last_seen_at=m.last_seen_at or m.updated_at,
            last_synced_at=m.last_synced_at or m.updated_at,
            raw_source_data=m.raw_source_data or {},
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def _snap_to_domain(self, m: ProductMarketSnapshotModel) -> ProductMarketSnapshot:
        return ProductMarketSnapshot(
            id=m.id,
            product_id=m.product_id,
            platform=m.platform,
            price=m.price or 0.0,
            original_price=m.original_price or 0.0,
            discount=m.discount or 0.0,
            rating=m.rating or 0.0,
            review_count=m.review_count or 0,
            stock_status=m.stock_status or "in_stock",
            observed_at=m.observed_at,
            created_at=m.created_at
        )

    def upsert_product(self, product: MarketplaceProduct) -> MarketplaceProduct:
        if not self.session:
            return product
        now = datetime.now(timezone.utc)
        m = self.session.query(MarketplaceProductModel).filter(
            MarketplaceProductModel.platform == product.platform.lower(),
            MarketplaceProductModel.product_id == str(product.product_id).strip()
        ).first()

        if m:
            m.product_name = product.product_name
            m.product_url = product.product_url
            m.image_url = product.image_url
            m.seller_name = product.seller_name
            m.seller_id = product.seller_id
            m.category = product.category
            m.price = product.price
            m.original_price = product.original_price
            m.discount_percentage = product.discount_percentage
            m.discount_label = product.discount_label
            m.rating = product.rating
            m.review_count = product.review_count
            m.stock_status = product.stock_status
            m.in_stock = product.in_stock
            m.currency = product.currency
            m.location = product.location
            m.last_seen_at = now
            m.last_synced_at = now
            m.raw_source_data = product.raw_source_data or {}
            m.updated_at = now
            self.session.commit()
            return self._prod_to_domain(m)
        else:
            m = MarketplaceProductModel(
                id=product.id or f"{product.platform}_{product.product_id}",
                platform=product.platform.lower(),
                product_id=str(product.product_id).strip(),
                product_name=product.product_name,
                product_url=product.product_url,
                image_url=product.image_url,
                seller_name=product.seller_name,
                seller_id=product.seller_id,
                category=product.category,
                price=product.price,
                original_price=product.original_price,
                discount_percentage=product.discount_percentage,
                discount_label=product.discount_label,
                rating=product.rating,
                review_count=product.review_count,
                stock_status=product.stock_status,
                in_stock=product.in_stock,
                currency=product.currency,
                location=product.location,
                first_seen_at=now,
                last_seen_at=now,
                last_synced_at=now,
                raw_source_data=product.raw_source_data or {},
                created_at=now,
                updated_at=now
            )
            self.session.add(m)
            self.session.commit()
            return self._prod_to_domain(m)

    def batch_upsert_products(self, products: List[MarketplaceProduct]) -> List[MarketplaceProduct]:
        if not self.session:
            return products
        res = []
        for p in products:
            res.append(self.upsert_product(p))
        return res

    def get_product(self, platform: str, product_id: str) -> Optional[MarketplaceProduct]:
        if not self.session:
            return None
        m = self.session.query(MarketplaceProductModel).filter(
            MarketplaceProductModel.platform == platform.lower(),
            MarketplaceProductModel.product_id == str(product_id).strip()
        ).first()
        return self._prod_to_domain(m) if m else None

    def list_products(
        self,
        platform: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[MarketplaceProduct]:
        if not self.session:
            return []
        query = self.session.query(MarketplaceProductModel)
        if platform and platform != "all":
            query = query.filter(MarketplaceProductModel.platform == platform.lower())
        if category and category != "all":
            query = query.filter(
                (MarketplaceProductModel.category.ilike(f"%{category}%")) |
                (MarketplaceProductModel.product_name.ilike(f"%{category}%"))
            )
        if search and search.strip():
            s = f"%{search.strip()}%"
            query = query.filter(
                (MarketplaceProductModel.product_name.ilike(s)) |
                (MarketplaceProductModel.seller_name.ilike(s)) |
                (MarketplaceProductModel.category.ilike(s))
            )
        query = query.order_by(
            MarketplaceProductModel.last_synced_at.desc(),
            MarketplaceProductModel.rating.desc()
        ).offset(offset).limit(limit)
        models = query.all()
        return [self._prod_to_domain(m) for m in models]

    def count_products(self, platform: Optional[str] = None, category: Optional[str] = None) -> int:
        if not self.session:
            return 0
        query = self.session.query(func.count(MarketplaceProductModel.id))
        if platform and platform != "all":
            query = query.filter(MarketplaceProductModel.platform == platform.lower())
        if category and category != "all":
            query = query.filter(MarketplaceProductModel.category.ilike(f"%{category}%"))
        return query.scalar() or 0

    def create_snapshot(self, snapshot: ProductMarketSnapshot) -> ProductMarketSnapshot:
        if not self.session:
            return snapshot
        m = ProductMarketSnapshotModel(
            id=snapshot.id or str(uuid.uuid4()),
            product_id=str(snapshot.product_id).strip(),
            platform=snapshot.platform.lower(),
            price=snapshot.price,
            original_price=snapshot.original_price,
            discount=snapshot.discount,
            rating=snapshot.rating,
            review_count=snapshot.review_count,
            stock_status=snapshot.stock_status,
            observed_at=snapshot.observed_at or datetime.now(timezone.utc),
            created_at=snapshot.created_at or datetime.now(timezone.utc)
        )
        self.session.add(m)
        self.session.commit()
        return snapshot

    def batch_create_snapshots(self, snapshots: List[ProductMarketSnapshot]) -> List[ProductMarketSnapshot]:
        if not self.session:
            return snapshots
        for s in snapshots:
            self.create_snapshot(s)
        return snapshots

    def get_snapshots(self, platform: str, product_id: str, limit: int = 50) -> List[ProductMarketSnapshot]:
        if not self.session:
            return []
        models = self.session.query(ProductMarketSnapshotModel).filter(
            ProductMarketSnapshotModel.platform == platform.lower(),
            ProductMarketSnapshotModel.product_id == str(product_id).strip()
        ).order_by(ProductMarketSnapshotModel.observed_at.desc()).limit(limit).all()
        return [self._snap_to_domain(m) for m in models]

    def get_latest_sync_metadata(self, platform: str = "daraz") -> Dict[str, Any]:
        if not self.session:
            return {
                "is_live": False,
                "data_source": "none",
                "last_synced_at": None,
                "data_age_seconds": None,
                "total_records": 0
            }
        latest = self.session.query(func.max(MarketplaceProductModel.last_synced_at)).filter(
            MarketplaceProductModel.platform == platform.lower()
        ).scalar()
        count = self.count_products(platform=platform)
        if not latest or count == 0:
            return {
                "is_live": False,
                "data_source": "none",
                "last_synced_at": None,
                "data_age_seconds": None,
                "total_records": 0
            }
        now = datetime.now(timezone.utc)
        age_seconds = int((now - latest).total_seconds()) if latest else None
        return {
            "is_live": age_seconds is not None and age_seconds < 300,
            "data_source": "daraz_live" if (age_seconds is not None and age_seconds < 300) else "database_cache",
            "last_synced_at": latest.isoformat() if latest else None,
            "data_age_seconds": max(0, age_seconds) if age_seconds is not None else None,
            "total_records": count
        }

    def save_auth_session(self, session: DarazAuthSession) -> DarazAuthSession:
        if not self.session:
            return session
        if os.getenv("TESTING") == "true" or os.getenv("PYTEST_CURRENT_TEST") or getattr(settings, "ENVIRONMENT", "").lower() == "test":
            return session
        token = (session.access_token or "").lower()
        if token.startswith("mock_") or token.startswith("test_") or token.startswith("fake_") or token.startswith("sentinel_"):
            return session

        now = datetime.now(timezone.utc)
        seller_id = str(session.seller_id or session.account or session.id).strip()
        seller_name = str(session.account or session.seller_id or "Daraz Seller").strip()

        m = self.session.query(DarazSellerModel).filter(
            DarazSellerModel.seller_id == seller_id
        ).first()

        raw_data = {
            "auth_session": session.model_dump(mode="json")
        }

        if m:
            m.seller_name = seller_name
            m.raw_data = raw_data
            m.updated_at = now
        else:
            m = DarazSellerModel(
                id=str(uuid.uuid4()),
                seller_id=seller_id,
                seller_name=seller_name,
                shop_url=f"https://www.daraz.pk/shop/{seller_id}",
                rating=4.5,
                positive_ratings_percentage=95.0,
                location="pk",
                is_official_store=True,
                total_products=0,
                raw_data=raw_data,
                created_at=now,
                updated_at=now
            )
            self.session.add(m)
        self.session.commit()
        return session

    def get_auth_session(self, seller_id_or_account: Optional[str] = None) -> Optional[DarazAuthSession]:
        if not self.session:
            return None
        query = self.session.query(DarazSellerModel)
        if seller_id_or_account:
            query = query.filter(DarazSellerModel.seller_id == str(seller_id_or_account).strip())

        sellers = query.order_by(DarazSellerModel.updated_at.desc()).all()
        for sel in sellers:
            if sel.raw_data and isinstance(sel.raw_data, dict):
                raw_sess = sel.raw_data.get("auth_session")
                if raw_sess and isinstance(raw_sess, dict) and raw_sess.get("access_token"):
                    return DarazAuthSession(**raw_sess)
        return None

    def list_auth_sessions(self) -> List[DarazAuthSession]:
        if not self.session:
            return []
        sellers = self.session.query(DarazSellerModel).order_by(DarazSellerModel.updated_at.desc()).all()
        sessions = []
        for sel in sellers:
            if sel.raw_data and isinstance(sel.raw_data, dict):
                raw_sess = sel.raw_data.get("auth_session")
                if raw_sess and isinstance(raw_sess, dict) and raw_sess.get("access_token"):
                    sessions.append(DarazAuthSession(**raw_sess))
        return sessions

    def get_provider_health(self, provider_name: str) -> Optional[DarazProviderHealth]:
        return None

    def update_provider_health(self, health: DarazProviderHealth) -> DarazProviderHealth:
        return health

    def list_provider_health(self) -> List[DarazProviderHealth]:
        return []

    def upsert_seller(self, seller: DarazSeller) -> DarazSeller:
        if not self.session:
            return seller
        now = datetime.now(timezone.utc)
        clean_id = str(seller.seller_id).strip()
        m = self.session.query(DarazSellerModel).filter(
            DarazSellerModel.seller_id == clean_id
        ).first()

        if m:
            m.seller_name = seller.seller_name
            m.shop_url = seller.shop_url
            m.rating = seller.rating
            m.positive_ratings_percentage = seller.positive_ratings_percentage
            m.location = seller.location
            m.is_official_store = seller.is_official_store
            m.total_products = seller.total_products
            m.raw_data = seller.raw_data or {}
            m.updated_at = now
            self.session.commit()
            return DarazSeller(
                id=m.id,
                seller_id=m.seller_id,
                seller_name=m.seller_name,
                shop_url=m.shop_url,
                rating=m.rating,
                positive_ratings_percentage=m.positive_ratings_percentage,
                location=m.location,
                is_official_store=m.is_official_store,
                total_products=m.total_products,
                raw_data=m.raw_data or {},
                created_at=m.created_at,
                updated_at=m.updated_at
            )
        else:
            m = DarazSellerModel(
                id=seller.id or f"seller_{clean_id}",
                seller_id=clean_id,
                seller_name=seller.seller_name,
                shop_url=seller.shop_url,
                rating=seller.rating,
                positive_ratings_percentage=seller.positive_ratings_percentage,
                location=seller.location,
                is_official_store=seller.is_official_store,
                total_products=seller.total_products,
                raw_data=seller.raw_data or {},
                created_at=now,
                updated_at=now
            )
            self.session.add(m)
            self.session.commit()
            return DarazSeller(
                id=m.id,
                seller_id=m.seller_id,
                seller_name=m.seller_name,
                shop_url=m.shop_url,
                rating=m.rating,
                positive_ratings_percentage=m.positive_ratings_percentage,
                location=m.location,
                is_official_store=m.is_official_store,
                total_products=m.total_products,
                raw_data=m.raw_data or {},
                created_at=m.created_at,
                updated_at=m.updated_at
            )

    def get_seller(self, seller_id: str) -> Optional[DarazSeller]:
        if not self.session:
            return None
        m = self.session.query(DarazSellerModel).filter(
            DarazSellerModel.seller_id == str(seller_id).strip()
        ).first()
        if not m:
            return None
        return DarazSeller(
            id=m.id,
            seller_id=m.seller_id,
            seller_name=m.seller_name,
            shop_url=m.shop_url,
            rating=m.rating,
            positive_ratings_percentage=m.positive_ratings_percentage,
            location=m.location,
            is_official_store=m.is_official_store,
            total_products=m.total_products,
            raw_data=m.raw_data or {},
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def list_sellers(self, limit: int = 50, offset: int = 0) -> List[DarazSeller]:
        if not self.session:
            return []
        models = self.session.query(DarazSellerModel).order_by(
            DarazSellerModel.updated_at.desc()
        ).offset(offset).limit(limit).all()
        return [
            DarazSeller(
                id=m.id,
                seller_id=m.seller_id,
                seller_name=m.seller_name,
                shop_url=m.shop_url,
                rating=m.rating,
                positive_ratings_percentage=m.positive_ratings_percentage,
                location=m.location,
                is_official_store=m.is_official_store,
                total_products=m.total_products,
                raw_data=m.raw_data or {},
                created_at=m.created_at,
                updated_at=m.updated_at
            ) for m in models
        ]

    def upsert_category(self, category: DarazCategory) -> DarazCategory:
        if not self.session:
            return category
        now = datetime.now(timezone.utc)
        clean_id = str(category.category_id).strip()
        m = self.session.query(DarazCategoryModel).filter(
            DarazCategoryModel.category_id == clean_id
        ).first()

        if m:
            m.parent_id = category.parent_id
            m.name = category.name
            m.slug = category.slug
            m.level = category.level
            m.leaf = category.leaf
            m.product_count = category.product_count
            m.raw_data = category.raw_data or {}
            m.updated_at = now
            self.session.commit()
            return DarazCategory(
                id=m.id,
                category_id=m.category_id,
                parent_id=m.parent_id,
                name=m.name,
                slug=m.slug,
                level=m.level,
                leaf=m.leaf,
                product_count=m.product_count,
                raw_data=m.raw_data or {},
                created_at=m.created_at,
                updated_at=m.updated_at
            )
        else:
            m = DarazCategoryModel(
                id=category.id or f"cat_{clean_id}",
                category_id=clean_id,
                parent_id=category.parent_id,
                name=category.name,
                slug=category.slug,
                level=category.level,
                leaf=category.leaf,
                product_count=category.product_count,
                raw_data=category.raw_data or {},
                created_at=now,
                updated_at=now
            )
            self.session.add(m)
            self.session.commit()
            return DarazCategory(
                id=m.id,
                category_id=m.category_id,
                parent_id=m.parent_id,
                name=m.name,
                slug=m.slug,
                level=m.level,
                leaf=m.leaf,
                product_count=m.product_count,
                raw_data=m.raw_data or {},
                created_at=m.created_at,
                updated_at=m.updated_at
            )

    def get_category(self, category_id: str) -> Optional[DarazCategory]:
        if not self.session:
            return None
        m = self.session.query(DarazCategoryModel).filter(
            DarazCategoryModel.category_id == str(category_id).strip()
        ).first()
        if not m:
            return None
        return DarazCategory(
            id=m.id,
            category_id=m.category_id,
            parent_id=m.parent_id,
            name=m.name,
            slug=m.slug,
            level=m.level,
            leaf=m.leaf,
            product_count=m.product_count,
            raw_data=m.raw_data or {},
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def list_categories(self, parent_id: Optional[str] = None) -> List[DarazCategory]:
        if not self.session:
            return []
        query = self.session.query(DarazCategoryModel)
        if parent_id is not None:
            query = query.filter(DarazCategoryModel.parent_id == str(parent_id).strip())
        models = query.order_by(DarazCategoryModel.level.asc(), DarazCategoryModel.name.asc()).all()
        return [
            DarazCategory(
                id=m.id,
                category_id=m.category_id,
                parent_id=m.parent_id,
                name=m.name,
                slug=m.slug,
                level=m.level,
                leaf=m.leaf,
                product_count=m.product_count,
                raw_data=m.raw_data or {},
                created_at=m.created_at,
                updated_at=m.updated_at
            ) for m in models
        ]

    def create_review(self, review: DarazReview) -> DarazReview:
        if not self.session:
            return review
        now = datetime.now(timezone.utc)
        m = DarazReviewModel(
            id=review.id or str(uuid.uuid4()),
            review_id=review.review_id,
            product_id=review.product_id,
            seller_id=review.seller_id,
            rating=review.rating,
            reviewer_name=review.reviewer_name,
            review_title=review.review_title,
            review_content=review.review_content,
            verified_purchase=review.verified_purchase,
            review_date=review.review_date or now,
            sentiment_score=review.sentiment_score,
            raw_data=review.raw_data or {},
            created_at=review.created_at or now
        )
        self.session.add(m)
        self.session.commit()
        return review

    def list_reviews(self, product_id: str, limit: int = 50) -> List[DarazReview]:
        if not self.session:
            return []
        models = self.session.query(DarazReviewModel).filter(
            DarazReviewModel.product_id == str(product_id).strip()
        ).order_by(DarazReviewModel.review_date.desc()).limit(limit).all()
        return [
            DarazReview(
                id=m.id,
                review_id=m.review_id,
                product_id=m.product_id,
                seller_id=m.seller_id,
                rating=m.rating,
                reviewer_name=m.reviewer_name,
                review_title=m.review_title,
                review_content=m.review_content,
                verified_purchase=m.verified_purchase,
                review_date=m.review_date,
                sentiment_score=m.sentiment_score,
                raw_data=m.raw_data or {},
                created_at=m.created_at
            ) for m in models
        ]

    def create_ingestion_run(self, run: DarazIngestionRun) -> DarazIngestionRun:
        if not self.session:
            return run
        now = datetime.now(timezone.utc)
        m = DarazIngestionRunModel(
            id=run.id or str(uuid.uuid4()),
            provider_name=run.provider_name,
            status=run.status,
            trigger_type=run.trigger_type,
            category=run.category,
            search_query=run.search_query,
            products_fetched=run.products_fetched,
            products_inserted=run.products_inserted,
            products_updated=run.products_updated,
            snapshots_created=run.snapshots_created,
            reviews_fetched=run.reviews_fetched,
            error_code=run.error_code,
            error_message=run.error_message,
            retry_count=run.retry_count,
            metadata_json=run.metadata_json or {},
            started_at=run.started_at or now,
            completed_at=run.completed_at,
            created_at=run.created_at or now
        )
        self.session.add(m)
        self.session.commit()
        return run

    def update_ingestion_run(self, run: DarazIngestionRun) -> DarazIngestionRun:
        if not self.session:
            return run
        m = self.session.query(DarazIngestionRunModel).filter(
            DarazIngestionRunModel.id == run.id
        ).first()
        if m:
            m.status = run.status
            m.products_fetched = run.products_fetched
            m.products_inserted = run.products_inserted
            m.products_updated = run.products_updated
            m.snapshots_created = run.snapshots_created
            m.reviews_fetched = run.reviews_fetched
            m.error_code = run.error_code
            m.error_message = run.error_message
            m.retry_count = run.retry_count
            m.metadata_json = run.metadata_json or {}
            m.completed_at = run.completed_at or datetime.now(timezone.utc)
            self.session.commit()
        return run

    def get_ingestion_run(self, run_id: str) -> Optional[DarazIngestionRun]:
        if not self.session:
            return None
        m = self.session.query(DarazIngestionRunModel).filter(
            DarazIngestionRunModel.id == run_id
        ).first()
        if not m:
            return None
        return DarazIngestionRun(
            id=m.id,
            provider_name=m.provider_name,
            status=m.status,
            trigger_type=m.trigger_type,
            category=m.category,
            search_query=m.search_query,
            products_fetched=m.products_fetched,
            products_inserted=m.products_inserted,
            products_updated=m.products_updated,
            snapshots_created=m.snapshots_created,
            reviews_fetched=m.reviews_fetched,
            error_code=m.error_code,
            error_message=m.error_message,
            retry_count=m.retry_count,
            metadata_json=m.metadata_json or {},
            started_at=m.started_at,
            completed_at=m.completed_at,
            created_at=m.created_at
        )

    def list_ingestion_runs(self, limit: int = 50) -> List[DarazIngestionRun]:
        if not self.session:
            return []
        models = self.session.query(DarazIngestionRunModel).order_by(
            DarazIngestionRunModel.started_at.desc()
        ).limit(limit).all()
        return [
            DarazIngestionRun(
                id=m.id,
                provider_name=m.provider_name,
                status=m.status,
                trigger_type=m.trigger_type,
                category=m.category,
                search_query=m.search_query,
                products_fetched=m.products_fetched,
                products_inserted=m.products_inserted,
                products_updated=m.products_updated,
                snapshots_created=m.snapshots_created,
                reviews_fetched=m.reviews_fetched,
                error_code=m.error_code,
                error_message=m.error_message,
                retry_count=m.retry_count,
                metadata_json=m.metadata_json or {},
                started_at=m.started_at,
                completed_at=m.completed_at,
                created_at=m.created_at
            ) for m in models
        ]

    def record_api_telemetry(self, telemetry: DarazApiTelemetry) -> DarazApiTelemetry:
        if not self.session:
            return telemetry
        now = datetime.now(timezone.utc)
        m = DarazApiTelemetryModel(
            id=telemetry.id or str(uuid.uuid4()),
            endpoint=telemetry.endpoint,
            method=telemetry.method,
            provider_name=telemetry.provider_name,
            status_code=telemetry.status_code,
            latency_ms=telemetry.latency_ms,
            success=telemetry.success,
            error_code=telemetry.error_code,
            error_message=telemetry.error_message,
            request_params=telemetry.request_params or {},
            response_size_bytes=telemetry.response_size_bytes,
            created_at=telemetry.created_at or now
        )
        self.session.add(m)
        self.session.commit()
        return telemetry

    def get_api_telemetry(self, limit: int = 100) -> List[DarazApiTelemetry]:
        if not self.session:
            return []
        models = self.session.query(DarazApiTelemetryModel).order_by(
            DarazApiTelemetryModel.created_at.desc()
        ).limit(limit).all()
        return [
            DarazApiTelemetry(
                id=m.id,
                endpoint=m.endpoint,
                method=m.method,
                provider_name=m.provider_name,
                status_code=m.status_code,
                latency_ms=m.latency_ms,
                success=m.success,
                error_code=m.error_code,
                error_message=m.error_message,
                request_params=m.request_params or {},
                response_size_bytes=m.response_size_bytes,
                created_at=m.created_at
            ) for m in models
        ]

    def get_or_create_daily_quota(self, date: Optional[str] = None, daily_limit: int = 6000000) -> DarazDailyQuota:
        if not self.session:
            today_str = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            now = datetime.now(timezone.utc)
            return DarazDailyQuota(
                id=f"quota_{today_str}",
                date=today_str,
                requests_used=0,
                daily_limit=daily_limit,
                remaining=daily_limit,
                rate_limit_hits=0,
                last_request_at=now,
                reset_at=None,
                created_at=now,
                updated_at=now
            )
        today_str = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now = datetime.now(timezone.utc)
        m = self.session.query(DarazDailyQuotaModel).filter(
            DarazDailyQuotaModel.date == today_str
        ).first()
        if not m:
            m = DarazDailyQuotaModel(
                id=f"quota_{today_str}",
                date=today_str,
                requests_used=0,
                daily_limit=daily_limit,
                remaining=daily_limit,
                rate_limit_hits=0,
                last_request_at=now,
                reset_at=None,
                created_at=now,
                updated_at=now
            )
            self.session.add(m)
            self.session.commit()
        return DarazDailyQuota(
            id=m.id,
            date=m.date,
            requests_used=m.requests_used,
            daily_limit=m.daily_limit,
            remaining=m.remaining,
            rate_limit_hits=m.rate_limit_hits,
            last_request_at=m.last_request_at,
            reset_at=m.reset_at,
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def increment_daily_quota(self, date: Optional[str] = None, count: int = 1, is_rate_limited: bool = False) -> DarazDailyQuota:
        if not self.session:
            today_str = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            now = datetime.now(timezone.utc)
            return DarazDailyQuota(
                id=f"quota_{today_str}",
                date=today_str,
                requests_used=count,
                daily_limit=6000000,
                remaining=max(0, 6000000 - count),
                rate_limit_hits=1 if is_rate_limited else 0,
                last_request_at=now,
                reset_at=None,
                created_at=now,
                updated_at=now
            )
        today_str = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now = datetime.now(timezone.utc)
        m = self.session.query(DarazDailyQuotaModel).filter(
            DarazDailyQuotaModel.date == today_str
        ).first()
        if not m:
            m = DarazDailyQuotaModel(
                id=f"quota_{today_str}",
                date=today_str,
                requests_used=count,
                daily_limit=6000000,
                remaining=max(0, 6000000 - count),
                rate_limit_hits=1 if is_rate_limited else 0,
                last_request_at=now,
                reset_at=None,
                created_at=now,
                updated_at=now
            )
            self.session.add(m)
        else:
            m.requests_used += count
            m.remaining = max(0, m.daily_limit - m.requests_used)
            if is_rate_limited:
                m.rate_limit_hits += 1
            m.last_request_at = now
            m.updated_at = now
        self.session.commit()
        return DarazDailyQuota(
            id=m.id,
            date=m.date,
            requests_used=m.requests_used,
            daily_limit=m.daily_limit,
            remaining=m.remaining,
            rate_limit_hits=m.rate_limit_hits,
            last_request_at=m.last_request_at,
            reset_at=m.reset_at,
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def add_training_dataset_item(self, item: DarazTrainingDataset) -> DarazTrainingDataset:
        if not self.session:
            return item
        now = datetime.now(timezone.utc)
        m = DarazTrainingDatasetModel(
            id=item.id or str(uuid.uuid4()),
            product_id=item.product_id,
            unified_product_id=item.unified_product_id,
            title=item.title,
            category=item.category,
            brand=item.brand,
            price=item.price,
            rating=item.rating,
            review_count=item.review_count,
            features=item.features or {},
            quality_score=item.quality_score,
            agent_label=item.agent_label,
            is_validated=item.is_validated,
            created_at=item.created_at or now
        )
        self.session.add(m)
        self.session.commit()
        return item

    def list_training_dataset(self, category: Optional[str] = None, limit: int = 100) -> List[DarazTrainingDataset]:
        if not self.session:
            return []
        query = self.session.query(DarazTrainingDatasetModel)
        if category and category != "all":
            query = query.filter(DarazTrainingDatasetModel.category.ilike(f"%{category}%"))
        models = query.order_by(
            DarazTrainingDatasetModel.quality_score.desc(),
            DarazTrainingDatasetModel.created_at.desc()
        ).limit(limit).all()
        return [
            DarazTrainingDataset(
                id=m.id,
                product_id=m.product_id,
                unified_product_id=m.unified_product_id,
                title=m.title,
                category=m.category,
                brand=m.brand,
                price=m.price,
                rating=m.rating,
                review_count=m.review_count,
                features=m.features or {},
                quality_score=m.quality_score,
                agent_label=m.agent_label,
                is_validated=m.is_validated,
                created_at=m.created_at
            ) for m in models
        ]


class PostgresShopifyRepository(ShopifyRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _to_domain(self, m: ShopifyProductModel) -> ShopifyProduct:
        return ShopifyProduct(
            id=m.id,
            store_domain=m.store_domain,
            product_id=m.product_id,
            title=m.title,
            handle=m.handle,
            product_url=m.product_url,
            image_url=m.image_url,
            images=m.images or [],
            vendor=m.vendor,
            product_type=m.product_type,
            category=m.category,
            tags=m.tags or [],
            price=m.price,
            compare_at_price=m.compare_at_price,
            discount_percentage=m.discount_percentage,
            discount_label=m.discount_label,
            currency=m.currency,
            available=m.available,
            rating=m.rating,
            review_count=m.review_count,
            source_provider=m.source_provider,
            variants_count=m.variants_count,
            first_seen_at=m.first_seen_at,
            last_seen_at=m.last_seen_at,
            last_synced_at=m.last_synced_at,
            raw_data=m.raw_data or {},
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def _snap_to_domain(self, m: ShopifyProductSnapshotModel) -> ShopifyProductSnapshot:
        return ShopifyProductSnapshot(
            id=m.id,
            shopify_product_id=m.shopify_product_id,
            store_domain=m.store_domain,
            product_id=m.product_id,
            price=m.price,
            compare_at_price=m.compare_at_price,
            available=m.available,
            rating=m.rating,
            review_count=m.review_count,
            inventory_status=m.inventory_status,
            source_provider=m.source_provider,
            observed_at=m.observed_at,
            raw_data=m.raw_data or {},
            created_at=m.created_at
        )

    def _health_to_domain(self, m: ShopifyProviderHealthModel) -> ShopifyProviderHealth:
        return ShopifyProviderHealth(
            id=m.id,
            provider_name=m.provider_name,
            priority=m.priority,
            enabled=m.enabled,
            status=m.status,
            consecutive_failures=m.consecutive_failures,
            total_requests=m.total_requests,
            successful_requests=m.successful_requests,
            failed_requests=m.failed_requests,
            rate_limited_requests=m.rate_limited_requests,
            last_success_at=m.last_success_at,
            last_failure_at=m.last_failure_at,
            cooldown_until=m.cooldown_until,
            last_error_code=m.last_error_code,
            last_error_message=m.last_error_message,
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def _run_to_domain(self, m: ShopifySyncRunModel) -> ShopifySyncRun:
        return ShopifySyncRun(
            id=m.id,
            store_domain=m.store_domain,
            provider_name=m.provider_name,
            status=m.status,
            products_fetched=m.products_fetched,
            products_inserted=m.products_inserted,
            products_updated=m.products_updated,
            snapshots_created=m.snapshots_created,
            provider_attempts=m.provider_attempts or [],
            error_code=m.error_code,
            error_message=m.error_message,
            started_at=m.started_at,
            completed_at=m.completed_at,
            created_at=m.created_at
        )

    def upsert_product(self, product: ShopifyProduct) -> ShopifyProduct:
        if not self.session:
            return product
        now = datetime.now(timezone.utc)
        m = self.session.query(ShopifyProductModel).filter(
            ShopifyProductModel.store_domain == product.store_domain.lower(),
            ShopifyProductModel.product_id == str(product.product_id).strip()
        ).first()

        if m:
            m.title = product.title
            m.handle = product.handle
            m.product_url = product.product_url
            m.image_url = product.image_url
            m.images = product.images
            m.vendor = product.vendor
            m.product_type = product.product_type
            m.category = product.category
            m.tags = product.tags
            m.price = product.price
            m.compare_at_price = product.compare_at_price
            m.discount_percentage = product.discount_percentage
            m.discount_label = product.discount_label
            m.currency = product.currency
            m.available = product.available
            m.rating = product.rating
            m.review_count = product.review_count
            m.source_provider = product.source_provider
            m.variants_count = product.variants_count
            m.last_seen_at = now
            m.last_synced_at = now
            m.raw_data = product.raw_data
            m.updated_at = now
            self.session.commit()
            return self._to_domain(m)
        else:
            new_m = ShopifyProductModel(
                id=product.id or f"sp_{uuid.uuid4().hex[:16]}",
                store_domain=product.store_domain.lower(),
                product_id=str(product.product_id).strip(),
                title=product.title,
                handle=product.handle,
                product_url=product.product_url,
                image_url=product.image_url,
                images=product.images,
                vendor=product.vendor,
                product_type=product.product_type,
                category=product.category,
                tags=product.tags,
                price=product.price,
                compare_at_price=product.compare_at_price,
                discount_percentage=product.discount_percentage,
                discount_label=product.discount_label,
                currency=product.currency,
                available=product.available,
                rating=product.rating,
                review_count=product.review_count,
                source_provider=product.source_provider,
                variants_count=product.variants_count,
                first_seen_at=product.first_seen_at or now,
                last_seen_at=now,
                last_synced_at=now,
                raw_data=product.raw_data,
                created_at=product.created_at or now,
                updated_at=now
            )
            self.session.add(new_m)
            self.session.commit()
            return self._to_domain(new_m)

    def batch_upsert_products(self, products: List[ShopifyProduct]) -> List[ShopifyProduct]:
        if not self.session:
            return products
        res = []
        for p in products:
            res.append(self.upsert_product(p))
        return res

    def get_product(self, store_domain: str, product_id: str) -> Optional[ShopifyProduct]:
        if not self.session:
            return None
        m = self.session.query(ShopifyProductModel).filter(
            ShopifyProductModel.store_domain == store_domain.lower(),
            ShopifyProductModel.product_id == str(product_id).strip()
        ).first()
        return self._to_domain(m) if m else None

    def get_product_by_id(self, id: str) -> Optional[ShopifyProduct]:
        if not self.session:
            return None
        m = self.session.query(ShopifyProductModel).filter(
            (ShopifyProductModel.id == id) | (ShopifyProductModel.product_id == id)
        ).first()
        return self._to_domain(m) if m else None

    def list_products(
        self,
        store_domain: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ShopifyProduct]:
        if not self.session:
            return []
        q = self.session.query(ShopifyProductModel)
        if store_domain and store_domain != "all":
            q = q.filter(ShopifyProductModel.store_domain.ilike(f"%{store_domain.strip()}%"))
        if category and category != "all":
            q = q.filter(
                (ShopifyProductModel.category.ilike(f"%{category.strip()}%")) |
                (ShopifyProductModel.product_type.ilike(f"%{category.strip()}%"))
            )
        if search and search.strip():
            s = f"%{search.strip()}%"
            q = q.filter(
                (ShopifyProductModel.title.ilike(s)) |
                (ShopifyProductModel.vendor.ilike(s)) |
                (ShopifyProductModel.category.ilike(s))
            )

        if sort_by == "price_asc":
            q = q.order_by(ShopifyProductModel.price.asc())
        elif sort_by == "price_desc":
            q = q.order_by(ShopifyProductModel.price.desc())
        elif sort_by == "rating":
            q = q.order_by(ShopifyProductModel.rating.desc(), ShopifyProductModel.review_count.desc())
        else:
            q = q.order_by(ShopifyProductModel.last_synced_at.desc())

        models = q.offset(offset).limit(limit).all()
        return [self._to_domain(m) for m in models]

    def count_products(
        self,
        store_domain: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> int:
        if not self.session:
            return 0
        q = self.session.query(func.count(ShopifyProductModel.id))
        if store_domain and store_domain != "all":
            q = q.filter(ShopifyProductModel.store_domain.ilike(f"%{store_domain.strip()}%"))
        if category and category != "all":
            q = q.filter(
                (ShopifyProductModel.category.ilike(f"%{category.strip()}%")) |
                (ShopifyProductModel.product_type.ilike(f"%{category.strip()}%"))
            )
        if search and search.strip():
            s = f"%{search.strip()}%"
            q = q.filter(
                (ShopifyProductModel.title.ilike(s)) |
                (ShopifyProductModel.vendor.ilike(s)) |
                (ShopifyProductModel.category.ilike(s))
            )
        return q.scalar() or 0

    def create_snapshot(self, snapshot: ShopifyProductSnapshot) -> ShopifyProductSnapshot:
        if not self.session:
            return snapshot
        m = ShopifyProductSnapshotModel(
            id=snapshot.id or f"sps_{uuid.uuid4().hex[:16]}",
            shopify_product_id=snapshot.shopify_product_id,
            store_domain=snapshot.store_domain.lower(),
            product_id=str(snapshot.product_id).strip(),
            price=snapshot.price,
            compare_at_price=snapshot.compare_at_price,
            available=snapshot.available,
            rating=snapshot.rating,
            review_count=snapshot.review_count,
            inventory_status=snapshot.inventory_status,
            source_provider=snapshot.source_provider,
            observed_at=snapshot.observed_at or datetime.now(timezone.utc),
            raw_data=snapshot.raw_data,
            created_at=snapshot.created_at or datetime.now(timezone.utc)
        )
        self.session.add(m)
        self.session.commit()
        return snapshot

    def batch_create_snapshots(self, snapshots: List[ShopifyProductSnapshot]) -> List[ShopifyProductSnapshot]:
        if not self.session:
            return snapshots
        for s in snapshots:
            self.create_snapshot(s)
        return snapshots

    def get_snapshots(self, store_domain: str, product_id: str, limit: int = 50) -> List[ShopifyProductSnapshot]:
        if not self.session:
            return []
        models = self.session.query(ShopifyProductSnapshotModel).filter(
            ShopifyProductSnapshotModel.store_domain == store_domain.lower(),
            ShopifyProductSnapshotModel.product_id == str(product_id).strip()
        ).order_by(ShopifyProductSnapshotModel.observed_at.desc()).limit(limit).all()
        return [self._snap_to_domain(m) for m in models]

    def get_provider_health(self, provider_name: str) -> Optional[ShopifyProviderHealth]:
        if not self.session:
            return None
        m = self.session.query(ShopifyProviderHealthModel).filter(
            ShopifyProviderHealthModel.provider_name == provider_name
        ).first()
        return self._health_to_domain(m) if m else None

    def list_provider_health(self) -> List[ShopifyProviderHealth]:
        if not self.session:
            return []
        models = self.session.query(ShopifyProviderHealthModel).order_by(
            ShopifyProviderHealthModel.priority.asc()
        ).all()
        return [self._health_to_domain(m) for m in models]

    def update_provider_health(self, health: ShopifyProviderHealth) -> ShopifyProviderHealth:
        if not self.session:
            return health
        now = datetime.now(timezone.utc)
        m = self.session.query(ShopifyProviderHealthModel).filter(
            ShopifyProviderHealthModel.provider_name == health.provider_name
        ).first()
        if m:
            m.status = health.status
            m.enabled = health.enabled
            m.consecutive_failures = health.consecutive_failures
            m.total_requests = health.total_requests
            m.successful_requests = health.successful_requests
            m.failed_requests = health.failed_requests
            m.rate_limited_requests = health.rate_limited_requests
            m.last_success_at = health.last_success_at
            m.last_failure_at = health.last_failure_at
            m.cooldown_until = health.cooldown_until
            m.last_error_code = health.last_error_code
            m.last_error_message = health.last_error_message
            m.updated_at = now
            self.session.commit()
            return self._health_to_domain(m)
        else:
            new_m = ShopifyProviderHealthModel(
                id=health.id or f"prov_{health.provider_name}",
                provider_name=health.provider_name,
                priority=health.priority,
                enabled=health.enabled,
                status=health.status,
                consecutive_failures=health.consecutive_failures,
                total_requests=health.total_requests,
                successful_requests=health.successful_requests,
                failed_requests=health.failed_requests,
                rate_limited_requests=health.rate_limited_requests,
                last_success_at=health.last_success_at,
                last_failure_at=health.last_failure_at,
                cooldown_until=health.cooldown_until,
                last_error_code=health.last_error_code,
                last_error_message=health.last_error_message,
                created_at=health.created_at or now,
                updated_at=now
            )
            self.session.add(new_m)
            self.session.commit()
            return self._health_to_domain(new_m)

    def record_sync_run(self, sync_run: ShopifySyncRun) -> ShopifySyncRun:
        if not self.session:
            return sync_run
        m = ShopifySyncRunModel(
            id=sync_run.id or f"ssr_{uuid.uuid4().hex[:16]}",
            store_domain=sync_run.store_domain.lower(),
            provider_name=sync_run.provider_name,
            status=sync_run.status,
            products_fetched=sync_run.products_fetched,
            products_inserted=sync_run.products_inserted,
            products_updated=sync_run.products_updated,
            snapshots_created=sync_run.snapshots_created,
            provider_attempts=sync_run.provider_attempts,
            error_code=sync_run.error_code,
            error_message=sync_run.error_message,
            started_at=sync_run.started_at or datetime.now(timezone.utc),
            completed_at=sync_run.completed_at,
            created_at=sync_run.created_at or datetime.now(timezone.utc)
        )
        self.session.add(m)
        self.session.commit()
        return sync_run

    def list_sync_runs(self, store_domain: Optional[str] = None, limit: int = 20) -> List[ShopifySyncRun]:
        if not self.session:
            return []
        q = self.session.query(ShopifySyncRunModel)
        if store_domain and store_domain != "all":
            q = q.filter(ShopifySyncRunModel.store_domain.ilike(f"%{store_domain.strip()}%"))
        models = q.order_by(ShopifySyncRunModel.started_at.desc()).limit(limit).all()
        return [self._run_to_domain(m) for m in models]

    def get_latest_sync_metadata(self, store_domain: Optional[str] = None) -> Dict[str, Any]:
        if not self.session:
            return {
                "is_live": False,
                "data_source": "none",
                "last_synced_at": None,
                "data_age_seconds": None,
                "total_records": 0
            }
        q = self.session.query(func.max(ShopifyProductModel.last_synced_at))
        if store_domain and store_domain != "all":
            q = q.filter(ShopifyProductModel.store_domain.ilike(f"%{store_domain.strip()}%"))
        latest = q.scalar()
        count = self.count_products(store_domain=store_domain)
        if not latest or count == 0:
            return {
                "is_live": False,
                "data_source": "none",
                "last_synced_at": None,
                "data_age_seconds": None,
                "total_records": 0
            }
        now = datetime.now(timezone.utc)
        age_seconds = int((now - latest).total_seconds()) if latest else None
        return {
            "is_live": age_seconds is not None and age_seconds < 300,
            "data_source": "shopify_live" if (age_seconds is not None and age_seconds < 300) else "database_cache",
            "last_synced_at": latest.isoformat() if latest else None,
            "data_age_seconds": max(0, age_seconds) if age_seconds is not None else None,
            "total_records": count
        }


class PostgresUnifiedProductRepository(UnifiedProductRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _product_to_domain(self, m: UnifiedProductModel) -> UnifiedProduct:
        return UnifiedProduct(
            id=m.id,
            unified_product_id=m.unified_product_id,
            canonical_name=m.canonical_name,
            normalized_name=m.normalized_name,
            brand=m.brand,
            category=m.category,
            subcategory=m.subcategory,
            product_type=m.product_type,
            description=m.description,
            primary_image=m.primary_image,
            identifiers=m.identifiers or {},
            first_seen_at=m.first_seen_at,
            last_seen_at=m.last_seen_at,
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def _listing_to_domain(self, m: ProductPlatformListingModel) -> ProductPlatformListing:
        return ProductPlatformListing(
            id=m.id,
            unified_product_id=m.unified_product_id,
            platform=m.platform,
            platform_product_id=m.platform_product_id,
            store_domain=m.store_domain,
            product_url=m.product_url,
            title=m.title,
            normalized_title=m.normalized_title,
            price=m.price,
            original_price=m.original_price,
            currency=m.currency,
            discount_percentage=m.discount_percentage,
            discount_label=m.discount_label,
            seller_name=m.seller_name,
            vendor=m.vendor,
            rating=m.rating,
            review_count=m.review_count,
            available=m.available,
            image_url=m.image_url,
            source_provider=m.source_provider,
            last_synced_at=m.last_synced_at,
            completeness_score=m.completeness_score,
            raw_data=m.raw_data or {},
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def upsert_unified_product(self, product: UnifiedProduct) -> UnifiedProduct:
        if not self.session:
            return product
        m = self.session.query(UnifiedProductModel).filter(
            UnifiedProductModel.unified_product_id == product.unified_product_id
        ).first()

        now = datetime.now(timezone.utc)
        if m:
            m.canonical_name = product.canonical_name
            m.normalized_name = product.normalized_name
            m.brand = product.brand
            m.category = product.category
            m.subcategory = product.subcategory
            m.product_type = product.product_type
            m.description = product.description
            m.primary_image = product.primary_image or m.primary_image
            m.identifiers = product.identifiers
            m.last_seen_at = product.last_seen_at or now
            m.updated_at = now
        else:
            m = UnifiedProductModel(
                id=product.id or f"up_{uuid.uuid4().hex[:12]}",
                unified_product_id=product.unified_product_id,
                canonical_name=product.canonical_name,
                normalized_name=product.normalized_name,
                brand=product.brand,
                category=product.category,
                subcategory=product.subcategory,
                product_type=product.product_type,
                description=product.description,
                primary_image=product.primary_image,
                identifiers=product.identifiers,
                first_seen_at=product.first_seen_at or now,
                last_seen_at=product.last_seen_at or now,
                created_at=product.created_at or now,
                updated_at=product.updated_at or now
            )
            self.session.add(m)
        self.session.commit()
        return self._product_to_domain(m)

    def get_unified_product(self, unified_product_id: str) -> Optional[UnifiedProduct]:
        if not self.session:
            return None
        m = self.session.query(UnifiedProductModel).filter(
            UnifiedProductModel.unified_product_id == unified_product_id
        ).first()
        return self._product_to_domain(m) if m else None

    def find_by_normalized_name(self, normalized_name: str) -> List[UnifiedProduct]:
        if not self.session:
            return []
        models = self.session.query(UnifiedProductModel).filter(
            UnifiedProductModel.normalized_name == normalized_name.strip().lower()
        ).all()
        return [self._product_to_domain(m) for m in models]

    def find_by_brand(self, brand: str) -> List[UnifiedProduct]:
        if not self.session:
            return []
        models = self.session.query(UnifiedProductModel).filter(
            UnifiedProductModel.brand.ilike(brand.strip())
        ).all()
        return [self._product_to_domain(m) for m in models]

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
    ) -> List[UnifiedProduct]:
        if not self.session:
            return []
        q = self.session.query(UnifiedProductModel)
        if category and category.lower() != "all":
            q = q.filter(UnifiedProductModel.category.ilike(f"%{category.strip()}%"))
        if brand and brand.lower() != "all":
            q = q.filter(UnifiedProductModel.brand.ilike(brand.strip()))
        if search and search.strip():
            term = f"%{search.strip()}%"
            q = q.filter(
                UnifiedProductModel.canonical_name.ilike(term) |
                UnifiedProductModel.normalized_name.ilike(term) |
                UnifiedProductModel.brand.ilike(term)
            )

        if platform and platform.lower() != "all":
            q = q.join(ProductPlatformListingModel).filter(
                ProductPlatformListingModel.platform.ilike(platform.strip())
            )

        if sort_by == "name_asc":
            q = q.order_by(UnifiedProductModel.canonical_name.asc())
        elif sort_by == "name_desc":
            q = q.order_by(UnifiedProductModel.canonical_name.desc())
        elif sort_by == "oldest":
            q = q.order_by(UnifiedProductModel.first_seen_at.asc())
        else:
            q = q.order_by(UnifiedProductModel.last_seen_at.desc())

        models = q.offset(offset).limit(limit).all()
        return [self._product_to_domain(m) for m in models]

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
    ) -> int:
        if not self.session:
            return 0
        q = self.session.query(func.count(UnifiedProductModel.id))
        if category and category.lower() != "all":
            q = q.filter(UnifiedProductModel.category.ilike(f"%{category.strip()}%"))
        if brand and brand.lower() != "all":
            q = q.filter(UnifiedProductModel.brand.ilike(brand.strip()))
        if search and search.strip():
            term = f"%{search.strip()}%"
            q = q.filter(
                UnifiedProductModel.canonical_name.ilike(term) |
                UnifiedProductModel.normalized_name.ilike(term) |
                UnifiedProductModel.brand.ilike(term)
            )
        if platform and platform.lower() != "all":
            q = q.join(ProductPlatformListingModel).filter(
                ProductPlatformListingModel.platform.ilike(platform.strip())
            )
        return q.scalar() or 0

    def upsert_platform_listing(self, listing: ProductPlatformListing) -> ProductPlatformListing:
        if not self.session:
            return listing
        dom = listing.store_domain or ""
        m = self.session.query(ProductPlatformListingModel).filter(
            ProductPlatformListingModel.platform == listing.platform,
            ProductPlatformListingModel.platform_product_id == listing.platform_product_id,
            ProductPlatformListingModel.store_domain == dom
        ).first()

        now = datetime.now(timezone.utc)
        if m:
            m.unified_product_id = listing.unified_product_id
            m.title = listing.title
            m.normalized_title = listing.normalized_title
            m.price = listing.price
            m.original_price = listing.original_price
            m.currency = listing.currency
            m.discount_percentage = listing.discount_percentage
            m.discount_label = listing.discount_label
            m.seller_name = listing.seller_name
            m.vendor = listing.vendor
            m.rating = listing.rating
            m.review_count = listing.review_count
            m.available = listing.available
            m.image_url = listing.image_url
            m.source_provider = listing.source_provider
            m.last_synced_at = listing.last_synced_at or now
            m.completeness_score = listing.completeness_score
            m.raw_data = listing.raw_data
            m.updated_at = now
        else:
            m = ProductPlatformListingModel(
                id=listing.id or f"list_{uuid.uuid4().hex[:12]}",
                unified_product_id=listing.unified_product_id,
                platform=listing.platform,
                platform_product_id=listing.platform_product_id,
                store_domain=dom,
                product_url=listing.product_url,
                title=listing.title,
                normalized_title=listing.normalized_title,
                price=listing.price,
                original_price=listing.original_price,
                currency=listing.currency,
                discount_percentage=listing.discount_percentage,
                discount_label=listing.discount_label,
                seller_name=listing.seller_name,
                vendor=listing.vendor,
                rating=listing.rating,
                review_count=listing.review_count,
                available=listing.available,
                image_url=listing.image_url,
                source_provider=listing.source_provider,
                last_synced_at=listing.last_synced_at or now,
                completeness_score=listing.completeness_score,
                raw_data=listing.raw_data,
                created_at=listing.created_at or now,
                updated_at=listing.updated_at or now
            )
            self.session.add(m)
        self.session.commit()
        return self._listing_to_domain(m)

    def get_platform_listing(self, platform: str, platform_product_id: str, store_domain: Optional[str] = None) -> Optional[ProductPlatformListing]:
        if not self.session:
            return None
        dom = store_domain or ""
        m = self.session.query(ProductPlatformListingModel).filter(
            ProductPlatformListingModel.platform == platform,
            ProductPlatformListingModel.platform_product_id == platform_product_id,
            ProductPlatformListingModel.store_domain == dom
        ).first()
        return self._listing_to_domain(m) if m else None

    def list_listings_for_product(self, unified_product_id: str) -> List[ProductPlatformListing]:
        if not self.session:
            return []
        models = self.session.query(ProductPlatformListingModel).filter(
            ProductPlatformListingModel.unified_product_id == unified_product_id
        ).all()
        return [self._listing_to_domain(m) for m in models]

    def list_all_listings(self) -> List[ProductPlatformListing]:
        if not self.session:
            return []
        models = self.session.query(ProductPlatformListingModel).all()
        return [self._listing_to_domain(m) for m in models]

    def record_match_audit(self, audit: ProductMatchAudit) -> ProductMatchAudit:
        if not self.session:
            return audit
        m = ProductMatchAuditModel(
            id=audit.id or f"audit_{uuid.uuid4().hex[:12]}",
            unified_product_id=audit.unified_product_id,
            platform=audit.platform,
            platform_product_id=audit.platform_product_id,
            matching_method=audit.matching_method,
            matching_confidence=audit.matching_confidence,
            matched_at=audit.matched_at or datetime.now(timezone.utc),
            details=audit.details,
            created_at=audit.created_at or datetime.now(timezone.utc)
        )
        self.session.add(m)
        self.session.commit()
        return audit

    def get_match_audit(self, unified_product_id: str) -> Optional[ProductMatchAudit]:
        if not self.session:
            return None
        m = self.session.query(ProductMatchAuditModel).filter(
            ProductMatchAuditModel.unified_product_id == unified_product_id
        ).order_by(ProductMatchAuditModel.matched_at.desc()).first()
        if m:
            return ProductMatchAudit(
                id=m.id,
                unified_product_id=m.unified_product_id,
                platform=m.platform,
                platform_product_id=m.platform_product_id,
                matching_method=m.matching_method,
                matching_confidence=m.matching_confidence,
                matched_at=m.matched_at,
                details=m.details or {},
                created_at=m.created_at
            )
        return None

    def list_match_audits(self, unified_product_id: Optional[str] = None, limit: int = 50) -> List[ProductMatchAudit]:
        if not self.session:
            return []
        q = self.session.query(ProductMatchAuditModel)
        if unified_product_id:
            q = q.filter(ProductMatchAuditModel.unified_product_id == unified_product_id)
        models = q.order_by(ProductMatchAuditModel.matched_at.desc()).limit(limit).all()
        return [
            ProductMatchAudit(
                id=m.id,
                unified_product_id=m.unified_product_id,
                platform=m.platform,
                platform_product_id=m.platform_product_id,
                matching_method=m.matching_method,
                matching_confidence=m.matching_confidence,
                matched_at=m.matched_at,
                details=m.details or {},
                created_at=m.created_at
            )
            for m in models
        ]

    def record_match_candidate(self, candidate: ProductMatchCandidate) -> ProductMatchCandidate:
        if not self.session:
            return candidate
        m = self.session.query(ProductMatchCandidateModel).filter(ProductMatchCandidateModel.id == candidate.id).first()
        if m:
            m.unified_product_id = candidate.unified_product_id
            m.candidate_unified_id = candidate.candidate_unified_id
            m.platform = candidate.platform
            m.platform_product_id = candidate.platform_product_id
            m.confidence_score = candidate.confidence_score
            m.method = candidate.method
            m.status = candidate.status
            m.reasons = candidate.reasons
        else:
            m = ProductMatchCandidateModel(
                id=candidate.id or f"cand_{uuid.uuid4().hex[:12]}",
                unified_product_id=candidate.unified_product_id,
                candidate_unified_id=candidate.candidate_unified_id,
                platform=candidate.platform,
                platform_product_id=candidate.platform_product_id,
                confidence_score=candidate.confidence_score,
                method=candidate.method,
                status=candidate.status,
                reasons=candidate.reasons,
                created_at=candidate.created_at or datetime.now(timezone.utc)
            )
            self.session.add(m)
        self.session.commit()
        return candidate

    def get_match_candidate(self, candidate_id: str) -> Optional[ProductMatchCandidate]:
        if not self.session:
            return None
        m = self.session.query(ProductMatchCandidateModel).filter(ProductMatchCandidateModel.id == candidate_id).first()
        if m:
            return ProductMatchCandidate(
                id=m.id,
                unified_product_id=m.unified_product_id,
                candidate_unified_id=m.candidate_unified_id,
                platform=m.platform,
                platform_product_id=m.platform_product_id,
                confidence_score=m.confidence_score,
                method=m.method,
                status=m.status,
                reasons=m.reasons or [],
                created_at=m.created_at
            )
        return None

    def update_match_candidate(self, candidate: ProductMatchCandidate) -> ProductMatchCandidate:
        return self.record_match_candidate(candidate)

    def list_match_candidates(
        self,
        unified_product_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ProductMatchCandidate]:
        if not self.session:
            return []
        q = self.session.query(ProductMatchCandidateModel)
        if unified_product_id:
            q = q.filter(
                (ProductMatchCandidateModel.unified_product_id == unified_product_id) |
                (ProductMatchCandidateModel.candidate_unified_id == unified_product_id)
            )
        if status:
            q = q.filter(ProductMatchCandidateModel.status.ilike(status.strip()))
        models = q.order_by(ProductMatchCandidateModel.created_at.desc()).offset(offset).limit(limit).all()
        return [
            ProductMatchCandidate(
                id=m.id,
                unified_product_id=m.unified_product_id,
                candidate_unified_id=m.candidate_unified_id,
                platform=m.platform,
                platform_product_id=m.platform_product_id,
                confidence_score=m.confidence_score,
                method=m.method,
                status=m.status,
                reasons=m.reasons or [],
                created_at=m.created_at
            )
            for m in models
        ]

    def record_match_decision(self, decision: ProductMatchDecision) -> ProductMatchDecision:
        if not self.session:
            return decision
        now = datetime.now(timezone.utc)
        m = ProductMatchDecisionModel(
            id=decision.id or f"pmd_{uuid.uuid4().hex[:12]}",
            product_a_id=decision.product_a_id,
            product_b_id=decision.product_b_id,
            unified_product_id=decision.unified_product_id,
            platform_a=decision.platform_a,
            platform_b=decision.platform_b,
            decision=decision.decision,
            confidence=decision.confidence,
            match_method=decision.match_method,
            reasons=decision.reasons,
            conflicts=decision.conflicts,
            variant_attributes=decision.variant_attributes,
            base_product_id=decision.base_product_id,
            llm_used=decision.llm_used,
            llm_provider=decision.llm_provider,
            llm_model=decision.llm_model,
            agent_id=decision.agent_id,
            agent_run_id=decision.agent_run_id,
            details=decision.details,
            created_at=decision.created_at or now,
            updated_at=decision.updated_at or now
        )
        self.session.add(m)
        self.session.commit()
        return decision

    def get_match_decision(self, decision_id: str) -> Optional[ProductMatchDecision]:
        if not self.session:
            return None
        m = self.session.query(ProductMatchDecisionModel).filter(ProductMatchDecisionModel.id == decision_id).first()
        if m:
            return ProductMatchDecision(
                id=m.id,
                product_a_id=m.product_a_id,
                product_b_id=m.product_b_id,
                unified_product_id=m.unified_product_id,
                platform_a=m.platform_a,
                platform_b=m.platform_b,
                decision=m.decision,
                confidence=m.confidence,
                match_method=m.match_method,
                reasons=m.reasons or [],
                conflicts=m.conflicts or [],
                variant_attributes=m.variant_attributes or {},
                base_product_id=m.base_product_id,
                llm_used=m.llm_used,
                llm_provider=m.llm_provider,
                llm_model=m.llm_model,
                agent_id=m.agent_id,
                agent_run_id=m.agent_run_id,
                details=m.details or {},
                created_at=m.created_at,
                updated_at=m.updated_at
            )
        return None

    def list_match_decisions(
        self,
        product_id: Optional[str] = None,
        unified_product_id: Optional[str] = None,
        limit: int = 50
    ) -> List[ProductMatchDecision]:
        if not self.session:
            return []
        q = self.session.query(ProductMatchDecisionModel)
        if product_id:
            q = q.filter(
                (ProductMatchDecisionModel.product_a_id == product_id) |
                (ProductMatchDecisionModel.product_b_id == product_id) |
                (ProductMatchDecisionModel.unified_product_id == product_id)
            )
        elif unified_product_id:
            q = q.filter(ProductMatchDecisionModel.unified_product_id == unified_product_id)
        models = q.order_by(ProductMatchDecisionModel.created_at.desc()).limit(limit).all()
        return [
            ProductMatchDecision(
                id=m.id,
                product_a_id=m.product_a_id,
                product_b_id=m.product_b_id,
                unified_product_id=m.unified_product_id,
                platform_a=m.platform_a,
                platform_b=m.platform_b,
                decision=m.decision,
                confidence=m.confidence,
                match_method=m.match_method,
                reasons=m.reasons or [],
                conflicts=m.conflicts or [],
                variant_attributes=m.variant_attributes or {},
                base_product_id=m.base_product_id,
                llm_used=m.llm_used,
                llm_provider=m.llm_provider,
                llm_model=m.llm_model,
                agent_id=m.agent_id,
                agent_run_id=m.agent_run_id,
                details=m.details or {},
                created_at=m.created_at,
                updated_at=m.updated_at
            )
            for m in models
        ]



class PostgresLLMUsageRepository(LLMUsageRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def record_usage(self, record: LLMUsageRecord) -> LLMUsageRecord:
        if not self.session:
            return record
        m = LLMUsageRecordModel(
            id=record.id or f"llm_use_{uuid.uuid4().hex[:16]}",
            user_id=record.user_id,
            workspace_id=record.workspace_id,
            provider=record.provider,
            model=record.model,
            request_type=record.request_type,
            prompt_version=record.prompt_version,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            total_tokens=record.total_tokens,
            estimated_cost=record.estimated_cost,
            latency_ms=record.latency_ms,
            status=record.status,
            error_code=record.error_code,
            created_at=record.created_at or datetime.now(timezone.utc)
        )
        self.session.add(m)
        self.session.commit()
        return record

    def list_usage(
        self,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        provider: Optional[str] = None,
        request_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[LLMUsageRecord]:
        if not self.session:
            return []
        q = self.session.query(LLMUsageRecordModel)
        if user_id:
            q = q.filter(LLMUsageRecordModel.user_id == user_id)
        if workspace_id:
            q = q.filter(LLMUsageRecordModel.workspace_id == workspace_id)
        if provider:
            q = q.filter(func.lower(LLMUsageRecordModel.provider) == provider.lower())
        if request_type:
            q = q.filter(func.lower(LLMUsageRecordModel.request_type) == request_type.lower())
        q = q.order_by(LLMUsageRecordModel.created_at.desc())
        models = q.offset(offset).limit(limit).all()
        return [
            LLMUsageRecord(
                id=m.id,
                user_id=m.user_id,
                workspace_id=m.workspace_id,
                provider=m.provider,
                model=m.model,
                request_type=m.request_type,
                prompt_version=m.prompt_version,
                input_tokens=m.input_tokens,
                output_tokens=m.output_tokens,
                total_tokens=m.total_tokens,
                estimated_cost=m.estimated_cost,
                latency_ms=m.latency_ms,
                status=m.status,
                error_code=m.error_code,
                created_at=m.created_at
            )
            for m in models
        ]

    def get_summary(self, user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        if not self.session:
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "cached_requests": 0,
                "failed_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
                "average_latency_ms": 0.0
            }
        q = self.session.query(LLMUsageRecordModel)
        if user_id:
            q = q.filter(LLMUsageRecordModel.user_id == user_id)
        if workspace_id:
            q = q.filter(LLMUsageRecordModel.workspace_id == workspace_id)
        records = q.all()

        total_requests = len(records)
        successful_requests = len([r for r in records if r.status == "success"])
        cached_requests = len([r for r in records if r.status == "cached"])
        failed_requests = len([r for r in records if r.status == "failed"])
        total_input_tokens = sum(r.input_tokens for r in records)
        total_output_tokens = sum(r.output_tokens for r in records)
        total_tokens = sum(r.total_tokens for r in records)
        total_cost = round(sum(r.estimated_cost for r in records), 6)
        avg_latency = round(sum(r.latency_ms for r in records) / max(1, total_requests), 2)

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "cached_requests": cached_requests,
            "failed_requests": failed_requests,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": total_cost,
            "average_latency_ms": avg_latency
        }


class PostgresDataQualityRepository(DataQualityRepository):
    """
    SQLAlchemy PostgreSQL repository for AI Agents and Data Quality validation.
    """

    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def get_agent(self, agent_id: str) -> Optional[AIAgent]:
        if not self.session:
            return None
        m = self.session.query(AIAgentModel).filter(AIAgentModel.id == agent_id).first()
        if not m:
            return None
        return AIAgent(
            id=m.id,
            name=m.name,
            slug=m.slug,
            agent_type=m.agent_type,
            status=m.status,
            description=m.description,
            version=m.version,
            capabilities=m.capabilities or [],
            configuration=m.configuration or {},
            metadata_json=m.metadata_json or {},
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def upsert_agent(self, agent: AIAgent) -> AIAgent:
        if not self.session:
            return agent
        m = self.session.query(AIAgentModel).filter(AIAgentModel.id == agent.id).first()
        now = datetime.now(timezone.utc)
        if m:
            m.name = agent.name
            m.slug = agent.slug
            m.agent_type = agent.agent_type
            m.status = agent.status
            m.description = agent.description
            m.version = agent.version
            m.capabilities = agent.capabilities
            m.configuration = agent.configuration
            m.metadata_json = agent.metadata_json
            m.updated_at = now
        else:
            m = AIAgentModel(
                id=agent.id,
                name=agent.name,
                slug=agent.slug,
                agent_type=agent.agent_type,
                status=agent.status,
                description=agent.description,
                version=agent.version,
                capabilities=agent.capabilities,
                configuration=agent.configuration,
                metadata_json=agent.metadata_json,
                created_at=now,
                updated_at=now
            )
            self.session.add(m)
        self.session.commit()
        return self.get_agent(agent.id) or agent

    def create_agent_run(self, run: AIAgentRun) -> AIAgentRun:
        if not self.session:
            return run
        m = AIAgentRunModel(
            id=run.id,
            agent_id=run.agent_id,
            workspace_id=run.workspace_id,
            run_type=run.run_type,
            status=run.status,
            trigger_source=run.trigger_source,
            items_processed=run.items_processed,
            items_valid=run.items_valid,
            items_warning=run.items_warning,
            items_needs_review=run.items_needs_review,
            items_rejected=run.items_rejected,
            avg_quality_score=run.avg_quality_score,
            gemini_calls_count=run.gemini_calls_count,
            execution_time_ms=run.execution_time_ms,
            started_at=run.started_at,
            completed_at=run.completed_at,
            error_message=run.error_message,
            metadata_json=run.metadata_json,
            created_at=run.created_at
        )
        self.session.add(m)
        self.session.commit()
        return run

    def update_agent_run(self, run: AIAgentRun) -> AIAgentRun:
        if not self.session:
            return run
        m = self.session.query(AIAgentRunModel).filter(AIAgentRunModel.id == run.id).first()
        if m:
            m.status = run.status
            m.items_processed = run.items_processed
            m.items_valid = run.items_valid
            m.items_warning = run.items_warning
            m.items_needs_review = run.items_needs_review
            m.items_rejected = run.items_rejected
            m.avg_quality_score = run.avg_quality_score
            m.gemini_calls_count = run.gemini_calls_count
            m.execution_time_ms = run.execution_time_ms
            m.completed_at = run.completed_at
            m.error_message = run.error_message
            m.metadata_json = run.metadata_json
            self.session.commit()
        else:
            self.create_agent_run(run)
        return run

    def get_agent_run(self, run_id: str) -> Optional[AIAgentRun]:
        if not self.session:
            return None
        m = self.session.query(AIAgentRunModel).filter(AIAgentRunModel.id == run_id).first()
        if not m:
            return None
        return AIAgentRun(
            id=m.id,
            agent_id=m.agent_id,
            workspace_id=m.workspace_id,
            run_type=m.run_type,
            status=m.status,
            trigger_source=m.trigger_source,
            items_processed=m.items_processed,
            items_valid=m.items_valid,
            items_warning=m.items_warning,
            items_needs_review=m.items_needs_review,
            items_rejected=m.items_rejected,
            avg_quality_score=m.avg_quality_score,
            gemini_calls_count=m.gemini_calls_count,
            execution_time_ms=m.execution_time_ms,
            started_at=m.started_at,
            completed_at=m.completed_at,
            error_message=m.error_message,
            metadata_json=m.metadata_json or {},
            created_at=m.created_at
        )

    def list_agent_runs(self, agent_id: str, workspace_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[AIAgentRun]:
        if not self.session:
            return []
        q = self.session.query(AIAgentRunModel).filter(AIAgentRunModel.agent_id == agent_id)
        if workspace_id:
            q = q.filter(AIAgentRunModel.workspace_id.in_([workspace_id, None]))
        q = q.order_by(AIAgentRunModel.started_at.desc()).offset(offset).limit(limit)
        return [
            AIAgentRun(
                id=m.id,
                agent_id=m.agent_id,
                workspace_id=m.workspace_id,
                run_type=m.run_type,
                status=m.status,
                trigger_source=m.trigger_source,
                items_processed=m.items_processed,
                items_valid=m.items_valid,
                items_warning=m.items_warning,
                items_needs_review=m.items_needs_review,
                items_rejected=m.items_rejected,
                avg_quality_score=m.avg_quality_score,
                gemini_calls_count=m.gemini_calls_count,
                execution_time_ms=m.execution_time_ms,
                started_at=m.started_at,
                completed_at=m.completed_at,
                error_message=m.error_message,
                metadata_json=m.metadata_json or {},
                created_at=m.created_at
            )
            for m in q.all()
        ]

    def get_memory(self, agent_id: str, memory_type: str, memory_key: str) -> Optional[AIAgentMemory]:
        if not self.session:
            return None
        m = self.session.query(AIAgentMemoryModel).filter(
            AIAgentMemoryModel.agent_id == agent_id,
            AIAgentMemoryModel.memory_type == memory_type,
            AIAgentMemoryModel.memory_key == memory_key
        ).first()
        if not m:
            return None
        return AIAgentMemory(
            id=m.id,
            agent_id=m.agent_id,
            memory_type=m.memory_type,
            memory_key=m.memory_key,
            memory_value=m.memory_value or {},
            confidence_score=m.confidence_score,
            occurrence_count=m.occurrence_count,
            last_observed_at=m.last_observed_at,
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def upsert_memory(self, memory: AIAgentMemory) -> AIAgentMemory:
        if not self.session:
            return memory
        m = self.session.query(AIAgentMemoryModel).filter(
            AIAgentMemoryModel.agent_id == memory.agent_id,
            AIAgentMemoryModel.memory_type == memory.memory_type,
            AIAgentMemoryModel.memory_key == memory.memory_key
        ).first()
        now = datetime.now(timezone.utc)
        if m:
            m.memory_value = memory.memory_value
            m.confidence_score = memory.confidence_score
            m.occurrence_count = memory.occurrence_count
            m.last_observed_at = now
            m.updated_at = now
        else:
            m = AIAgentMemoryModel(
                id=memory.id,
                agent_id=memory.agent_id,
                memory_type=memory.memory_type,
                memory_key=memory.memory_key,
                memory_value=memory.memory_value,
                confidence_score=memory.confidence_score,
                occurrence_count=memory.occurrence_count,
                last_observed_at=now,
                created_at=now,
                updated_at=now
            )
            self.session.add(m)
        self.session.commit()
        return self.get_memory(memory.agent_id, memory.memory_type, memory.memory_key) or memory

    def list_memories(self, agent_id: str, memory_type: Optional[str] = None) -> List[AIAgentMemory]:
        if not self.session:
            return []
        q = self.session.query(AIAgentMemoryModel).filter(AIAgentMemoryModel.agent_id == agent_id)
        if memory_type:
            q = q.filter(AIAgentMemoryModel.memory_type == memory_type)
        q = q.order_by(AIAgentMemoryModel.last_observed_at.desc())
        return [
            AIAgentMemory(
                id=m.id,
                agent_id=m.agent_id,
                memory_type=m.memory_type,
                memory_key=m.memory_key,
                memory_value=m.memory_value or {},
                confidence_score=m.confidence_score,
                occurrence_count=m.occurrence_count,
                last_observed_at=m.last_observed_at,
                created_at=m.created_at,
                updated_at=m.updated_at
            )
            for m in q.all()
        ]

    def record_memory_event(self, event: AIAgentMemoryEvent) -> AIAgentMemoryEvent:
        if not self.session:
            return event
        m = AIAgentMemoryEventModel(
            id=event.id,
            agent_id=event.agent_id,
            memory_id=event.memory_id,
            event_type=event.event_type,
            old_value=event.old_value,
            new_value=event.new_value,
            reason=event.reason,
            trigger_run_id=event.trigger_run_id,
            created_at=event.created_at
        )
        self.session.add(m)
        self.session.commit()
        return event

    def list_memory_events(self, agent_id: str, memory_id: Optional[str] = None, limit: int = 50) -> List[AIAgentMemoryEvent]:
        if not self.session:
            return []
        q = self.session.query(AIAgentMemoryEventModel).filter(AIAgentMemoryEventModel.agent_id == agent_id)
        if memory_id:
            q = q.filter(AIAgentMemoryEventModel.memory_id == memory_id)
        q = q.order_by(AIAgentMemoryEventModel.created_at.desc()).limit(limit)
        return [
            AIAgentMemoryEvent(
                id=m.id,
                agent_id=m.agent_id,
                memory_id=m.memory_id,
                event_type=m.event_type,
                old_value=m.old_value,
                new_value=m.new_value or {},
                reason=m.reason,
                trigger_run_id=m.trigger_run_id,
                created_at=m.created_at
            )
            for m in q.all()
        ]

    def _to_domain(self, m: DataQualityValidationResultModel) -> DataQualityValidationResult:
        return DataQualityValidationResult(
            id=m.id,
            agent_id=m.agent_id or "agent_data_quality",
            run_id=m.run_id,
            workspace_id=m.workspace_id,
            platform=m.platform,
            source_provider=m.source_provider,
            platform_product_id=m.platform_product_id,
            unified_product_id=m.unified_product_id,
            product_title=m.product_title,
            product_name=m.product_name or m.product_title,
            original_category=m.original_category,
            normalized_category=m.normalized_category or "Unknown",
            data_quality_category=m.data_quality_category or "",
            product_url=m.product_url,
            image_url=m.image_url,
            price=m.price,
            currency=m.currency or "PKR",
            rating=m.rating,
            review_count=m.review_count or 0,
            availability=m.availability if m.availability is not None else True,
            overall_score=m.overall_score,
            quality_score=m.quality_score or m.overall_score,
            classification=m.classification,
            is_trusted=m.is_trusted,
            issues=[DataQualityRuleViolation(**i) if isinstance(i, dict) else i for i in (m.issues or [])],
            warnings=[DataQualityRuleViolation(**w) if isinstance(w, dict) else w for w in (m.warnings or [])],
            rejection_reasons=m.rejection_reasons or [],
            missing_fields=m.missing_fields or [],
            invalid_fields=m.invalid_fields or [],
            suspicious_fields=m.suspicious_fields or [],
            field_scores=m.field_scores or {},
            raw_payload_hash=m.raw_payload_hash,
            used_llm=m.used_llm,
            llm_used=m.llm_used or m.used_llm,
            llm_provider=m.llm_provider or "gemini",
            llm_resolution=m.llm_resolution,
            raw_payload=m.raw_payload or {},
            validated_at=m.validated_at,
            created_at=m.created_at,
            updated_at=m.updated_at or m.created_at
        )

    def _to_public_item(self, v: DataQualityValidationResult) -> PublicDataQualityItem:
        status_map = {
            "rejected": "Rejected By Data Quality Checks",
            "valid_with_warnings": "Real Data With Warnings",
            "needs_review": "Needs Review",
            "valid": "Real Data"
        }
        pub_status = status_map.get(v.classification.lower(), "Real Data")
        dq_cat = "Data Quality Issues" if v.classification.lower() == "rejected" else (v.data_quality_category or "")
        norm_cat = v.normalized_category or "Unknown"

        reasons = v.rejection_reasons or []
        if not reasons and v.classification.lower() == "rejected":
            reasons = [iss.message for iss in v.issues]

        issues_dict = [iss.model_dump(mode="json") if hasattr(iss, "model_dump") else iss for iss in (v.issues or [])]
        warnings_dict = [w.model_dump(mode="json") if hasattr(w, "model_dump") else w for w in (v.warnings or [])]

        return PublicDataQualityItem(
            id=v.id,
            product_id=v.platform_product_id or "",
            product_name=v.product_name or v.product_title or "Untitled Product",
            platform=v.platform,
            provider=v.source_provider,
            data_quality_category=dq_cat,
            original_category=v.original_category,
            normalized_category=norm_cat,
            price=v.price,
            currency=v.currency or "PKR",
            rating=v.rating,
            review_count=v.review_count or 0,
            availability=v.availability,
            image=v.image_url,
            product_url=v.product_url,
            quality_score=v.quality_score or v.overall_score,
            classification=v.classification,
            public_status=pub_status,
            issues=issues_dict,
            warnings=warnings_dict,
            rejection_reasons=reasons,
            missing_fields=v.missing_fields or [],
            invalid_fields=v.invalid_fields or [],
            suspicious_fields=v.suspicious_fields or [],
            llm_used=v.llm_used or v.used_llm,
            last_validated_time=v.validated_at
        )

    def save_validation_result(self, result: DataQualityValidationResult) -> DataQualityValidationResult:
        if not self.session:
            return result
        issues_json = [i.model_dump(mode="json") if hasattr(i, "model_dump") else i for i in result.issues]
        warnings_json = [w.model_dump(mode="json") if hasattr(w, "model_dump") else w for w in result.warnings]
        m = DataQualityValidationResultModel(
            id=result.id,
            agent_id=result.agent_id or "agent_data_quality",
            run_id=result.run_id,
            workspace_id=result.workspace_id,
            platform=result.platform,
            source_provider=result.source_provider,
            platform_product_id=result.platform_product_id,
            unified_product_id=result.unified_product_id,
            product_title=result.product_title,
            product_name=result.product_name or result.product_title,
            original_category=result.original_category,
            normalized_category=result.normalized_category or "Unknown",
            data_quality_category=result.data_quality_category or "",
            product_url=result.product_url,
            image_url=result.image_url,
            price=result.price,
            currency=result.currency or "PKR",
            rating=result.rating,
            review_count=result.review_count or 0,
            availability=result.availability,
            overall_score=result.overall_score,
            quality_score=result.quality_score or result.overall_score,
            classification=result.classification,
            is_trusted=result.is_trusted,
            issues=issues_json,
            warnings=warnings_json,
            rejection_reasons=result.rejection_reasons or [],
            missing_fields=result.missing_fields or [],
            invalid_fields=result.invalid_fields or [],
            suspicious_fields=result.suspicious_fields or [],
            field_scores=result.field_scores or {},
            raw_payload_hash=result.raw_payload_hash,
            used_llm=result.used_llm,
            llm_used=result.llm_used or result.used_llm,
            llm_provider=result.llm_provider or "gemini",
            llm_resolution=result.llm_resolution,
            raw_payload=result.raw_payload or {},
            validated_at=result.validated_at,
            created_at=result.created_at,
            updated_at=result.updated_at or result.created_at
        )
        self.session.add(m)
        self.session.commit()
        return result

    def get_validation_result(self, result_id: str) -> Optional[DataQualityValidationResult]:
        if not self.session:
            return None
        m = self.session.query(DataQualityValidationResultModel).filter(DataQualityValidationResultModel.id == result_id).first()
        if not m:
            return None
        return self._to_domain(m)

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
    ) -> List[DataQualityValidationResult]:
        if not self.session:
            return []
        q = self.session.query(DataQualityValidationResultModel)
        if workspace_id:
            q = q.filter(DataQualityValidationResultModel.workspace_id.in_([workspace_id, None]))
        if platform and platform != "all":
            q = q.filter(DataQualityValidationResultModel.platform.ilike(platform))
        if classification and classification != "all":
            q = q.filter(DataQualityValidationResultModel.classification.ilike(classification))
        if source_provider and source_provider != "all":
            q = q.filter(DataQualityValidationResultModel.source_provider.ilike(source_provider))
        if min_score is not None:
            q = q.filter(DataQualityValidationResultModel.overall_score >= min_score)
        if max_score is not None:
            q = q.filter(DataQualityValidationResultModel.overall_score <= max_score)
        rows = q.order_by(DataQualityValidationResultModel.validated_at.desc()).offset(offset).limit(limit).all()
        return [self._to_domain(r) for r in rows]

    def count_validation_results(
        self,
        workspace_id: Optional[str] = None,
        platform: Optional[str] = None,
        classification: Optional[str] = None,
        source_provider: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None
    ) -> int:
        if not self.session:
            return 0
        q = self.session.query(func.count(DataQualityValidationResultModel.id))
        if workspace_id:
            q = q.filter(DataQualityValidationResultModel.workspace_id.in_([workspace_id, None]))
        if platform:
            q = q.filter(DataQualityValidationResultModel.platform.ilike(platform))
        if classification:
            q = q.filter(DataQualityValidationResultModel.classification.ilike(classification))
        if source_provider:
            q = q.filter(DataQualityValidationResultModel.source_provider.ilike(source_provider))
        if min_score is not None:
            q = q.filter(DataQualityValidationResultModel.overall_score >= min_score)
        if max_score is not None:
            q = q.filter(DataQualityValidationResultModel.overall_score <= max_score)
        return q.scalar() or 0

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
    ) -> Tuple[List[PublicDataQualityItem], int]:
        if not self.session:
            return [], 0
        q = self.session.query(DataQualityValidationResultModel)
        if platform and platform != "all":
            q = q.filter(DataQualityValidationResultModel.platform.ilike(platform))
        if provider and provider != "all":
            q = q.filter(DataQualityValidationResultModel.source_provider.ilike(provider))
        if classification and classification != "all":
            q = q.filter(DataQualityValidationResultModel.classification.ilike(classification))
        if normalized_category and normalized_category != "all":
            cat_pattern = f"%{normalized_category}%"
            q = q.filter(
                (DataQualityValidationResultModel.normalized_category.ilike(cat_pattern)) |
                (DataQualityValidationResultModel.original_category.ilike(cat_pattern))
            )
        if search and search.strip():
            s_pattern = f"%{search.strip()}%"
            q = q.filter(
                (DataQualityValidationResultModel.product_name.ilike(s_pattern)) |
                (DataQualityValidationResultModel.product_title.ilike(s_pattern)) |
                (DataQualityValidationResultModel.platform_product_id.ilike(s_pattern)) |
                (DataQualityValidationResultModel.normalized_category.ilike(s_pattern)) |
                (DataQualityValidationResultModel.original_category.ilike(s_pattern))
            )
        if min_score is not None:
            q = q.filter(DataQualityValidationResultModel.overall_score >= min_score)
        if max_score is not None:
            q = q.filter(DataQualityValidationResultModel.overall_score <= max_score)
        if date_from is not None:
            q = q.filter(DataQualityValidationResultModel.validated_at >= date_from)
        if date_to is not None:
            q = q.filter(DataQualityValidationResultModel.validated_at <= date_to)

        # Sorting
        if sort_by == "score_asc":
            q = q.order_by(DataQualityValidationResultModel.overall_score.asc())
        elif sort_by == "score_desc":
            q = q.order_by(DataQualityValidationResultModel.overall_score.desc())
        elif sort_by == "price_asc":
            q = q.order_by(DataQualityValidationResultModel.price.asc())
        elif sort_by == "price_desc":
            q = q.order_by(DataQualityValidationResultModel.price.desc())
        elif sort_by == "validated_at_asc":
            q = q.order_by(DataQualityValidationResultModel.validated_at.asc())
        else:
            # Default: validated_at_desc
            q = q.order_by(DataQualityValidationResultModel.validated_at.desc())

        total = q.count()
        rows = q.offset(offset).limit(limit).all()
        items = [self._to_public_item(self._to_domain(r)) for r in rows]
        return items, total

    def get_public_stats(self) -> PublicDataQualityStatsResponse:
        if not self.session:
            return PublicDataQualityStatsResponse()

        results = self.session.query(DataQualityValidationResultModel).all()
        total = len(results)
        rejected = len([v for v in results if v.classification.lower() == "rejected"])
        warnings = len([v for v in results if v.classification.lower() == "valid_with_warnings"])
        valid = len([v for v in results if v.classification.lower() == "valid"])
        avg_score = round(sum(v.overall_score for v in results) / max(1, total), 1) if total else 100.0

        reason_counts: Dict[str, int] = {}
        for v in results:
            if v.classification.lower() == "rejected":
                for r in v.rejection_reasons or []:
                    reason_counts[r] = reason_counts.get(r, 0) + 1
                if not v.rejection_reasons:
                    for iss in v.issues or []:
                        msg = iss.get("message") if isinstance(iss, dict) else getattr(iss, "message", str(iss))
                        reason_counts[msg] = reason_counts.get(msg, 0) + 1
        top_reasons = [{"reason": k, "count": v} for k, v in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:10]]

        plat_counts: Dict[str, Dict[str, Any]] = {}
        for v in results:
            p = v.platform
            if p not in plat_counts:
                plat_counts[p] = {"platform": p, "total": 0, "rejected": 0, "valid": 0, "warnings": 0}
            plat_counts[p]["total"] += 1
            if v.classification.lower() == "rejected":
                plat_counts[p]["rejected"] += 1
            elif v.classification.lower() == "valid_with_warnings":
                plat_counts[p]["warnings"] += 1
            elif v.classification.lower() == "valid":
                plat_counts[p]["valid"] += 1
        platform_breakdown = list(plat_counts.values())

        cat_counts: Dict[str, Dict[str, Any]] = {}
        for v in results:
            cat = v.normalized_category or "Unknown"
            if cat not in cat_counts:
                cat_counts[cat] = {"category": cat, "total": 0, "rejected": 0}
            cat_counts[cat]["total"] += 1
            if v.classification.lower() == "rejected":
                cat_counts[cat]["rejected"] += 1
        cat_breakdown = sorted(list(cat_counts.values()), key=lambda x: x["total"], reverse=True)[:10]

        latest_time = max([v.validated_at for v in results], default=datetime.now(timezone.utc))

        return PublicDataQualityStatsResponse(
            total_inspected=total,
            total_rejected=rejected,
            total_warnings=warnings,
            total_valid=valid,
            rejection_rate=round((rejected / max(1, total)) * 100, 1),
            clean_rate=round((valid / max(1, total)) * 100, 1),
            average_quality_score=avg_score,
            top_rejection_reasons=top_reasons,
            platform_breakdown=platform_breakdown,
            category_breakdown=cat_breakdown,
            last_updated=latest_time
        )

    def get_product_validation_history(
        self,
        platform: str,
        platform_product_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[DataQualityValidationResult]:
        if not self.session:
            return []
        rows = self.session.query(DataQualityValidationResultModel).filter(
            DataQualityValidationResultModel.platform.ilike(platform),
            DataQualityValidationResultModel.platform_product_id == str(platform_product_id).strip()
        ).order_by(DataQualityValidationResultModel.validated_at.desc()).offset(offset).limit(limit).all()
        return [self._to_domain(r) for r in rows]

    def get_quality_summary(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        if not self.session:
            return {
                "total_products_validated": 0,
                "valid_count": 0,
                "warning_count": 0,
                "needs_review_count": 0,
                "rejected_count": 0,
                "overall_average_score": 100.0,
                "total_memory_items": 0,
                "provider_reliabilities": [],
                "total_runs": 0,
                "last_run_at": None
            }
        q = self.session.query(DataQualityValidationResultModel)
        if workspace_id:
            q = q.filter(DataQualityValidationResultModel.workspace_id.in_([workspace_id, None]))
        results = q.all()

        total = len(results)
        valid = len([v for v in results if v.classification == "valid"])
        warning = len([v for v in results if v.classification == "valid_with_warnings"])
        review = len([v for v in results if v.classification == "needs_review"])
        rejected = len([v for v in results if v.classification == "rejected"])
        avg_score = round(sum(v.overall_score for v in results) / max(1, total), 1) if total else 100.0

        # Memory count
        mem_count = self.session.query(func.count(AIAgentMemoryModel.id)).filter(AIAgentMemoryModel.agent_id == "agent_data_quality").scalar() or 0
        runs_count = self.session.query(func.count(AIAgentRunModel.id)).filter(AIAgentRunModel.agent_id == "agent_data_quality").scalar() or 0
        last_run = self.session.query(AIAgentRunModel).filter(AIAgentRunModel.agent_id == "agent_data_quality").order_by(AIAgentRunModel.started_at.desc()).first()

        # Provider breakdown
        providers = list(set(v.source_provider for v in results))
        provider_stats = []
        for p in providers:
            p_items = [v for v in results if v.source_provider == p]
            p_total = len(p_items)
            p_val = len([v for v in p_items if v.classification == "valid"])
            p_warn = len([v for v in p_items if v.classification == "valid_with_warnings"])
            p_rej = len([v for v in p_items if v.classification == "rejected"])
            p_score = round(sum(v.overall_score for v in p_items) / max(1, p_total), 1)

            issue_counts = {}
            for v in p_items:
                for iss in (v.issues or []) + (v.warnings or []):
                    r_name = iss.get("rule_name") if isinstance(iss, dict) else getattr(iss, "rule_name", "unknown")
                    issue_counts[r_name] = issue_counts.get(r_name, 0) + 1
            top_issues = [k for k, _ in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:3]]

            provider_stats.append({
                "provider": p,
                "platform": p_items[0].platform if p_items else "unknown",
                "total_evaluated": p_total,
                "valid_rate": round(p_val / max(1, p_total), 2),
                "warning_rate": round(p_warn / max(1, p_total), 2),
                "rejection_rate": round(p_rej / max(1, p_total), 2),
                "avg_score": p_score,
                "top_issues": top_issues
            })

        return {
            "total_products_validated": total,
            "valid_count": valid,
            "warning_count": warning,
            "needs_review_count": review,
            "rejected_count": rejected,
            "overall_average_score": avg_score,
            "total_memory_items": mem_count,
            "provider_reliabilities": provider_stats,
            "total_runs": runs_count,
            "last_run_at": last_run.started_at if last_run else None
        }

    def clear(self):
        if self.session:
            self.session.query(DataQualityValidationResultModel).delete()
            self.session.query(AIAgentMemoryEventModel).delete()
            self.session.query(AIAgentMemoryModel).delete()
            self.session.query(AIAgentRunModel).delete()
            self.session.commit()


class PostgresTaxonomyRepository(TaxonomyRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def get_category_by_id(self, category_id: str) -> Optional[TaxonomyCategory]:
        if not self.session:
            return None
        m = self.session.query(TaxonomyCategoryModel).filter(TaxonomyCategoryModel.id == category_id).first()
        if not m:
            return None
        return TaxonomyCategory(
            id=m.id,
            parent_id=m.parent_id,
            name=m.name,
            slug=m.slug,
            level=m.level,
            description=m.description or "",
            is_active=m.is_active,
            metadata_json=m.metadata_json or {},
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def get_category_by_slug(self, slug: str) -> Optional[TaxonomyCategory]:
        if not self.session:
            return None
        m = self.session.query(TaxonomyCategoryModel).filter(func.lower(TaxonomyCategoryModel.slug) == slug.strip().lower()).first()
        if not m:
            return None
        return TaxonomyCategory(
            id=m.id,
            parent_id=m.parent_id,
            name=m.name,
            slug=m.slug,
            level=m.level,
            description=m.description or "",
            is_active=m.is_active,
            metadata_json=m.metadata_json or {},
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def list_categories(self, parent_id: Optional[str] = None, level: Optional[int] = None) -> List[TaxonomyCategory]:
        if not self.session:
            return []
        q = self.session.query(TaxonomyCategoryModel)
        if parent_id is not None:
            if parent_id == "null" or parent_id == "":
                q = q.filter(TaxonomyCategoryModel.parent_id.is_(None))
            else:
                q = q.filter(TaxonomyCategoryModel.parent_id == parent_id)
        if level is not None:
            q = q.filter(TaxonomyCategoryModel.level == level)
        q = q.order_by(TaxonomyCategoryModel.level.asc(), TaxonomyCategoryModel.name.asc())
        return [
            TaxonomyCategory(
                id=m.id,
                parent_id=m.parent_id,
                name=m.name,
                slug=m.slug,
                level=m.level,
                description=m.description or "",
                is_active=m.is_active,
                metadata_json=m.metadata_json or {},
                created_at=m.created_at,
                updated_at=m.updated_at
            )
            for m in q.all()
        ]

    def get_taxonomy_tree(self) -> List[TaxonomyCategory]:
        if not self.session:
            return []
        all_cats = self.session.query(TaxonomyCategoryModel).order_by(TaxonomyCategoryModel.level.asc(), TaxonomyCategoryModel.name.asc()).all()
        counts = self.get_category_product_counts()

        # Build dictionary map
        nodes: Dict[str, TaxonomyCategory] = {}
        for m in all_cats:
            nodes[m.id] = TaxonomyCategory(
                id=m.id,
                parent_id=m.parent_id,
                name=m.name,
                slug=m.slug,
                level=m.level,
                description=m.description or "",
                is_active=m.is_active,
                metadata_json=m.metadata_json or {},
                product_count=counts.get(m.name, 0),
                children=[],
                created_at=m.created_at,
                updated_at=m.updated_at
            )

        root_nodes: List[TaxonomyCategory] = []
        for n in nodes.values():
            if n.parent_id and n.parent_id in nodes:
                nodes[n.parent_id].children.append(n)
            elif not n.parent_id:
                root_nodes.append(n)

        return root_nodes

    def search_categories(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.session:
            return []
        q_str = f"%{query.strip().lower()}%"
        matches = self.session.query(TaxonomyCategoryModel).filter(
            (func.lower(TaxonomyCategoryModel.name).like(q_str)) |
            (func.lower(TaxonomyCategoryModel.slug).like(q_str)) |
            (func.lower(TaxonomyCategoryModel.description).like(q_str))
        ).limit(limit).all()

        counts = self.get_category_product_counts()
        results = []
        for m in matches:
            path = [m.name]
            curr_p = m.parent_id
            while curr_p:
                p_m = self.session.query(TaxonomyCategoryModel).filter(TaxonomyCategoryModel.id == curr_p).first()
                if p_m:
                    path.insert(0, p_m.name)
                    curr_p = p_m.parent_id
                else:
                    break
            results.append({
                "id": m.id,
                "name": m.name,
                "slug": m.slug,
                "level": m.level,
                "path": path,
                "product_count": counts.get(m.name, 0)
            })
        return results

    def create_category(self, category: TaxonomyCategory) -> TaxonomyCategory:
        if not self.session:
            return category
        m = TaxonomyCategoryModel(
            id=category.id,
            parent_id=category.parent_id,
            name=category.name,
            slug=category.slug,
            level=category.level,
            description=category.description,
            is_active=category.is_active,
            metadata_json=category.metadata_json,
            created_at=category.created_at,
            updated_at=category.updated_at
        )
        self.session.add(m)
        self.session.commit()
        return category

    def update_category(self, category: TaxonomyCategory) -> TaxonomyCategory:
        if not self.session:
            return category
        m = self.session.query(TaxonomyCategoryModel).filter(TaxonomyCategoryModel.id == category.id).first()
        if m:
            m.name = category.name
            m.slug = category.slug
            m.level = category.level
            m.description = category.description
            m.is_active = category.is_active
            m.metadata_json = category.metadata_json
            m.updated_at = category.updated_at
            self.session.commit()
        return category

    def get_assignment_by_unified_product_id(self, unified_product_id: str) -> Optional[ProductTaxonomyAssignment]:
        if not self.session:
            return None
        m = self.session.query(ProductTaxonomyAssignmentModel).filter(
            ProductTaxonomyAssignmentModel.unified_product_id == unified_product_id.strip()
        ).order_by(ProductTaxonomyAssignmentModel.created_at.desc()).first()

        if not m:
            return None

        return ProductTaxonomyAssignment(
            id=m.id,
            unified_product_id=m.unified_product_id,
            category=m.category,
            subcategory=m.subcategory,
            product_type=m.product_type,
            taxonomy_path=m.taxonomy_path or [],
            brand=m.brand,
            attributes=m.attributes or {},
            confidence=m.confidence,
            classification_method=m.classification_method,
            needs_review=m.needs_review,
            agent_id=m.agent_id,
            agent_run_id=m.agent_run_id,
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def get_assignment_history(self, unified_product_id: str, limit: int = 50) -> List[ProductTaxonomyAssignment]:
        if not self.session:
            return []
        matches = self.session.query(ProductTaxonomyAssignmentModel).filter(
            ProductTaxonomyAssignmentModel.unified_product_id == unified_product_id.strip()
        ).order_by(ProductTaxonomyAssignmentModel.created_at.desc()).limit(limit).all()

        return [
            ProductTaxonomyAssignment(
                id=m.id,
                unified_product_id=m.unified_product_id,
                category=m.category,
                subcategory=m.subcategory,
                product_type=m.product_type,
                taxonomy_path=m.taxonomy_path or [],
                brand=m.brand,
                attributes=m.attributes or {},
                confidence=m.confidence,
                classification_method=m.classification_method,
                needs_review=m.needs_review,
                agent_id=m.agent_id,
                agent_run_id=m.agent_run_id,
                created_at=m.created_at,
                updated_at=m.updated_at
            )
            for m in matches
        ]

    def upsert_assignment(self, assignment: ProductTaxonomyAssignment) -> ProductTaxonomyAssignment:
        if not self.session:
            return assignment
        m = self.session.query(ProductTaxonomyAssignmentModel).filter(ProductTaxonomyAssignmentModel.id == assignment.id).first()
        if m:
            m.category = assignment.category
            m.subcategory = assignment.subcategory
            m.product_type = assignment.product_type
            m.taxonomy_path = assignment.taxonomy_path
            m.brand = assignment.brand
            m.attributes = assignment.attributes
            m.confidence = assignment.confidence
            m.classification_method = assignment.classification_method
            m.needs_review = assignment.needs_review
            m.agent_id = assignment.agent_id
            m.agent_run_id = assignment.agent_run_id
            m.updated_at = assignment.updated_at
        else:
            m = ProductTaxonomyAssignmentModel(
                id=assignment.id,
                unified_product_id=assignment.unified_product_id,
                category=assignment.category,
                subcategory=assignment.subcategory,
                product_type=assignment.product_type,
                taxonomy_path=assignment.taxonomy_path,
                brand=assignment.brand,
                attributes=assignment.attributes,
                confidence=assignment.confidence,
                classification_method=assignment.classification_method,
                needs_review=assignment.needs_review,
                agent_id=assignment.agent_id,
                agent_run_id=assignment.agent_run_id,
                created_at=assignment.created_at,
                updated_at=assignment.updated_at
            )
            self.session.add(m)
        self.session.commit()
        return assignment

    def create_candidate(self, candidate: ProductTaxonomyCandidate) -> ProductTaxonomyCandidate:
        if not self.session:
            return candidate
        m = ProductTaxonomyCandidateModel(
            id=candidate.id,
            product_id=candidate.product_id,
            unified_product_id=candidate.unified_product_id,
            candidate_category=candidate.candidate_category,
            candidate_subcategory=candidate.candidate_subcategory,
            candidate_product_type=candidate.candidate_product_type,
            confidence=candidate.confidence,
            reason=candidate.reason,
            metadata_json=candidate.metadata_json,
            created_at=candidate.created_at
        )
        self.session.add(m)
        self.session.commit()
        return candidate

    def list_candidates(self, limit: int = 50, offset: int = 0) -> List[ProductTaxonomyCandidate]:
        if not self.session:
            return []
        q = self.session.query(ProductTaxonomyCandidateModel).order_by(ProductTaxonomyCandidateModel.created_at.desc()).offset(offset).limit(limit)
        return [
            ProductTaxonomyCandidate(
                id=m.id,
                product_id=m.product_id,
                unified_product_id=m.unified_product_id,
                candidate_category=m.candidate_category,
                candidate_subcategory=m.candidate_subcategory,
                candidate_product_type=m.candidate_product_type,
                confidence=m.confidence,
                reason=m.reason,
                metadata_json=m.metadata_json or {},
                created_at=m.created_at
            )
            for m in q.all()
        ]

    def get_category_product_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        if not self.session:
            return counts
        rows = self.session.query(
            ProductTaxonomyAssignmentModel.category,
            func.count(ProductTaxonomyAssignmentModel.id)
        ).group_by(ProductTaxonomyAssignmentModel.category).all()
        for cat, cnt in rows:
            if cat:
                counts[cat] = cnt
        return counts

    def get_memory(self, agent_id: str, memory_type: str, memory_key: str) -> Optional[AIAgentMemory]:
        if not self.session:
            return None
        m = self.session.query(AIAgentMemoryModel).filter(
            AIAgentMemoryModel.agent_id == agent_id,
            AIAgentMemoryModel.memory_type == memory_type,
            AIAgentMemoryModel.memory_key == memory_key.strip().lower()
        ).first()
        if not m:
            return None
        return AIAgentMemory(
            id=m.id,
            agent_id=m.agent_id,
            memory_type=m.memory_type,
            memory_key=m.memory_key,
            memory_value=m.memory_value or {},
            confidence_score=m.confidence_score,
            occurrence_count=m.occurrence_count,
            last_observed_at=m.last_observed_at,
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def upsert_memory(self, memory: AIAgentMemory) -> AIAgentMemory:
        if not self.session:
            return memory
        m = self.session.query(AIAgentMemoryModel).filter(
            AIAgentMemoryModel.agent_id == memory.agent_id,
            AIAgentMemoryModel.memory_type == memory.memory_type,
            AIAgentMemoryModel.memory_key == memory.memory_key.strip().lower()
        ).first()
        if m:
            m.memory_value = memory.memory_value
            m.confidence_score = memory.confidence_score
            m.occurrence_count = memory.occurrence_count
            m.last_observed_at = memory.last_observed_at
            m.updated_at = memory.updated_at
        else:
            m = AIAgentMemoryModel(
                id=memory.id,
                agent_id=memory.agent_id,
                memory_type=memory.memory_type,
                memory_key=memory.memory_key.strip().lower(),
                memory_value=memory.memory_value,
                confidence_score=memory.confidence_score,
                occurrence_count=memory.occurrence_count,
                last_observed_at=memory.last_observed_at,
                created_at=memory.created_at,
                updated_at=memory.updated_at
            )
            self.session.add(m)
        self.session.commit()
        return memory

    def list_memory(self, agent_id: str, memory_type: Optional[str] = None) -> List[AIAgentMemory]:
        if not self.session:
            return []
        q = self.session.query(AIAgentMemoryModel).filter(AIAgentMemoryModel.agent_id == agent_id)
        if memory_type:
            q = q.filter(AIAgentMemoryModel.memory_type == memory_type)
        q = q.order_by(AIAgentMemoryModel.updated_at.desc())
        return [
            AIAgentMemory(
                id=m.id,
                agent_id=m.agent_id,
                memory_type=m.memory_type,
                memory_key=m.memory_key,
                memory_value=m.memory_value or {},
                confidence_score=m.confidence_score,
                occurrence_count=m.occurrence_count,
                last_observed_at=m.last_observed_at,
                created_at=m.created_at,
                updated_at=m.updated_at
            )
            for m in q.all()
        ]

    def record_memory_event(self, event: AIAgentMemoryEvent) -> AIAgentMemoryEvent:
        if not self.session:
            return event
        m = AIAgentMemoryEventModel(
            id=event.id,
            agent_id=event.agent_id,
            memory_id=event.memory_id,
            event_type=event.event_type,
            old_value=event.old_value,
            new_value=event.new_value,
            reason=event.reason,
            trigger_run_id=event.trigger_run_id,
            created_at=event.created_at
        )
        self.session.add(m)
        self.session.commit()
        return event

    def get_memory_events(self, agent_id: str, memory_id: Optional[str] = None, limit: int = 50) -> List[AIAgentMemoryEvent]:
        if not self.session:
            return []
        q = self.session.query(AIAgentMemoryEventModel).filter(AIAgentMemoryEventModel.agent_id == agent_id)
        if memory_id:
            q = q.filter(AIAgentMemoryEventModel.memory_id == memory_id)
        q = q.order_by(AIAgentMemoryEventModel.created_at.desc()).limit(limit)
        return [
            AIAgentMemoryEvent(
                id=m.id,
                agent_id=m.agent_id,
                memory_id=m.memory_id,
                event_type=m.event_type,
                old_value=m.old_value,
                new_value=m.new_value or {},
                reason=m.reason,
                trigger_run_id=m.trigger_run_id,
                created_at=m.created_at
            )
            for m in q.all()
        ]

    def clear(self):
        if self.session:
            self.session.query(ProductTaxonomyCandidateModel).delete()
            self.session.query(ProductTaxonomyAssignmentModel).delete()
            self.session.query(TaxonomyCategoryModel).delete()
            self.session.commit()


class PostgresScraperRepository(ScraperRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session
        self._health_cache: Dict[str, ScraperMarketplaceHealth] = {}
        self._init_defaults()

    def _init_defaults(self):
        defaults = ["daraz", "amazon", "ebay", "aliexpress", "shopify"]
        for m in defaults:
            self._health_cache[m] = ScraperMarketplaceHealth(
                marketplace=m,
                status="healthy",
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                challenge_count=0,
                average_latency_ms=0.0
            )

    def create_job(self, job: ScraperCrawlJob) -> ScraperCrawlJob:
        if not self.session:
            return job
        m = ScraperCrawlJobModel(
            id=job.id,
            marketplace=job.marketplace,
            trigger_type=job.trigger_type,
            keywords=job.keywords,
            urls=job.urls,
            category_id=job.category_id,
            target_count=job.target_count,
            max_workers=job.max_workers,
            status=job.status,
            products_fetched=job.products_fetched,
            products_persisted=job.products_persisted,
            products_rejected=job.products_rejected,
            challenged_count=job.challenged_count,
            failed_count=job.failed_count,
            current_throughput=job.current_throughput,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
            metadata_json=job.metadata_json,
            created_at=job.created_at,
            updated_at=job.updated_at
        )
        self.session.add(m)
        self.session.commit()
        return job

    def get_job(self, job_id: str) -> Optional[ScraperCrawlJob]:
        if not self.session:
            return None
        m = self.session.query(ScraperCrawlJobModel).filter(ScraperCrawlJobModel.id == job_id).first()
        if not m:
            return None
        return ScraperCrawlJob(
            id=m.id,
            marketplace=m.marketplace,
            trigger_type=m.trigger_type,
            keywords=m.keywords or [],
            urls=m.urls or [],
            category_id=m.category_id,
            target_count=m.target_count,
            max_workers=m.max_workers,
            status=m.status,
            products_fetched=m.products_fetched,
            products_persisted=m.products_persisted,
            products_rejected=m.products_rejected,
            challenged_count=m.challenged_count,
            failed_count=m.failed_count,
            current_throughput=m.current_throughput,
            error_message=m.error_message,
            started_at=m.started_at,
            completed_at=m.completed_at,
            metadata_json=m.metadata_json or {},
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    def update_job(self, job: ScraperCrawlJob) -> ScraperCrawlJob:
        if not self.session:
            return job
        m = self.session.query(ScraperCrawlJobModel).filter(ScraperCrawlJobModel.id == job.id).first()
        if m:
            m.status = job.status
            m.products_fetched = job.products_fetched
            m.products_persisted = job.products_persisted
            m.products_rejected = job.products_rejected
            m.challenged_count = job.challenged_count
            m.failed_count = job.failed_count
            m.current_throughput = job.current_throughput
            m.error_message = job.error_message
            m.started_at = job.started_at
            m.completed_at = job.completed_at
            m.metadata_json = job.metadata_json
            m.updated_at = datetime.now(timezone.utc)
            self.session.commit()
        return job

    def list_jobs(
        self,
        marketplace: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ScraperCrawlJob]:
        if not self.session:
            return []
        q = self.session.query(ScraperCrawlJobModel)
        if marketplace and marketplace != "all":
            q = q.filter(ScraperCrawlJobModel.marketplace == marketplace)
        if status and status != "all":
            q = q.filter(ScraperCrawlJobModel.status == status)
        q = q.order_by(ScraperCrawlJobModel.created_at.desc()).offset(offset).limit(limit)
        return [
            ScraperCrawlJob(
                id=m.id,
                marketplace=m.marketplace,
                trigger_type=m.trigger_type,
                keywords=m.keywords or [],
                urls=m.urls or [],
                category_id=m.category_id,
                target_count=m.target_count,
                max_workers=m.max_workers,
                status=m.status,
                products_fetched=m.products_fetched,
                products_persisted=m.products_persisted,
                products_rejected=m.products_rejected,
                challenged_count=m.challenged_count,
                failed_count=m.failed_count,
                current_throughput=m.current_throughput,
                error_message=m.error_message,
                started_at=m.started_at,
                completed_at=m.completed_at,
                metadata_json=m.metadata_json or {},
                created_at=m.created_at,
                updated_at=m.updated_at
            )
            for m in q.all()
        ]

    def count_jobs(
        self,
        marketplace: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        if not self.session:
            return 0
        q = self.session.query(func.count(ScraperCrawlJobModel.id))
        if marketplace and marketplace != "all":
            q = q.filter(ScraperCrawlJobModel.marketplace == marketplace)
        if status and status != "all":
            q = q.filter(ScraperCrawlJobModel.status == status)
        return q.scalar() or 0

    def save_raw_payload(self, payload: RawScrapedPayload) -> RawScrapedPayload:
        if not self.session:
            return payload
        m = self.session.query(RawScrapedPayloadModel).filter(
            RawScrapedPayloadModel.marketplace == payload.marketplace,
            RawScrapedPayloadModel.product_id == payload.product_id
        ).first()
        if m:
            m.crawl_job_id = payload.crawl_job_id
            m.source_url = payload.source_url
            m.canonical_url = payload.canonical_url
            m.raw_payload = payload.raw_payload
            m.normalized_payload = payload.normalized_payload
            m.parser_version = payload.parser_version
            m.extraction_status = payload.extraction_status
            m.quality_status = payload.quality_status
            m.confidence_score = payload.confidence_score
            m.scraped_at = payload.scraped_at
        else:
            m = RawScrapedPayloadModel(
                id=payload.id,
                marketplace=payload.marketplace,
                product_id=payload.product_id,
                crawl_job_id=payload.crawl_job_id,
                source_url=payload.source_url,
                canonical_url=payload.canonical_url,
                raw_payload=payload.raw_payload,
                normalized_payload=payload.normalized_payload,
                parser_version=payload.parser_version,
                extraction_status=payload.extraction_status,
                quality_status=payload.quality_status,
                confidence_score=payload.confidence_score,
                scraped_at=payload.scraped_at,
                created_at=payload.created_at
            )
            self.session.add(m)
        self.session.commit()
        return payload

    def get_raw_payload(self, marketplace: str, product_id: str) -> Optional[RawScrapedPayload]:
        if not self.session:
            return None
        m = self.session.query(RawScrapedPayloadModel).filter(
            RawScrapedPayloadModel.marketplace == marketplace,
            RawScrapedPayloadModel.product_id == product_id
        ).first()
        if not m:
            return None
        return RawScrapedPayload(
            id=m.id,
            marketplace=m.marketplace,
            product_id=m.product_id,
            crawl_job_id=m.crawl_job_id,
            source_url=m.source_url,
            canonical_url=m.canonical_url,
            raw_payload=m.raw_payload or {},
            normalized_payload=m.normalized_payload or {},
            parser_version=m.parser_version,
            extraction_status=m.extraction_status,
            quality_status=m.quality_status,
            confidence_score=m.confidence_score,
            scraped_at=m.scraped_at,
            created_at=m.created_at
        )

    def list_raw_payloads(
        self,
        marketplace: Optional[str] = None,
        crawl_job_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[RawScrapedPayload]:
        if not self.session:
            return []
        q = self.session.query(RawScrapedPayloadModel)
        if marketplace and marketplace != "all":
            q = q.filter(RawScrapedPayloadModel.marketplace == marketplace)
        if crawl_job_id:
            q = q.filter(RawScrapedPayloadModel.crawl_job_id == crawl_job_id)
        q = q.order_by(RawScrapedPayloadModel.scraped_at.desc()).offset(offset).limit(limit)
        return [
            RawScrapedPayload(
                id=m.id,
                marketplace=m.marketplace,
                product_id=m.product_id,
                crawl_job_id=m.crawl_job_id,
                source_url=m.source_url,
                canonical_url=m.canonical_url,
                raw_payload=m.raw_payload or {},
                normalized_payload=m.normalized_payload or {},
                parser_version=m.parser_version,
                extraction_status=m.extraction_status,
                quality_status=m.quality_status,
                confidence_score=m.confidence_score,
                scraped_at=m.scraped_at,
                created_at=m.created_at
            )
            for m in q.all()
        ]

    def record_marketplace_health(self, health: ScraperMarketplaceHealth) -> ScraperMarketplaceHealth:
        self._health_cache[health.marketplace.lower()] = health.model_copy()
        return health

    def get_marketplace_health(self, marketplace: str) -> Optional[ScraperMarketplaceHealth]:
        return self._health_cache.get(marketplace.lower())

    def list_marketplace_health(self) -> List[ScraperMarketplaceHealth]:
        return list(self._health_cache.values())

    def clear(self):
        if self.session:
            self.session.query(RawScrapedPayloadModel).delete()
            self.session.query(ScraperCrawlJobModel).delete()
            self.session.commit()


class PostgresMarketIntelligenceRepository(MarketIntelligenceRepository):
    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def _snapshot_to_domain(self, m: MarketIntelligenceSnapshotModel) -> MarketIntelligenceSnapshot:
        return MarketIntelligenceSnapshot(
            id=m.id,
            product_id=m.product_id,
            unified_product_id=m.unified_product_id,
            marketplace=m.marketplace,
            category=m.category,
            current_price=m.current_price,
            historical_price=m.historical_price,
            price_change_pct=m.price_change_pct,
            currency=m.currency,
            rating=m.rating,
            review_count=m.review_count,
            availability=m.availability,
            market_score=m.market_score,
            market_score_breakdown=m.market_score_breakdown or {},
            demand_score=m.demand_score,
            demand_level=m.demand_level,
            trend_velocity=m.trend_velocity,
            growth_7d=m.growth_7d,
            growth_30d=m.growth_30d,
            viral_score=m.viral_score,
            viral_level=m.viral_level,
            opportunity_score=m.opportunity_score,
            opportunity_level=m.opportunity_level,
            social_mentions_count=m.social_mentions_count,
            social_total_views=m.social_total_views,
            social_total_engagement=m.social_total_engagement,
            confidence_score=m.confidence_score,
            data_quality_score=m.data_quality_score,
            source_provenance=m.source_provenance,
            ai_summary=m.ai_summary,
            calculated_at=m.calculated_at,
            created_at=m.created_at
        )

    def _social_to_domain(self, m: SocialSignalModel) -> SocialSignal:
        return SocialSignal(
            id=m.id,
            platform=m.platform,
            external_id=m.external_id,
            content_title=m.content_title,
            content_url=m.content_url,
            author_name=m.author_name,
            views=m.views,
            likes=m.likes,
            comments=m.comments,
            shares=m.shares,
            engagement_rate=m.engagement_rate,
            matched_product_id=m.matched_product_id,
            matched_unified_id=m.matched_unified_id,
            match_confidence=m.match_confidence,
            observed_at=m.observed_at,
            raw_metadata=m.raw_metadata or {},
            created_at=m.created_at
        )

    def save_snapshot(self, snapshot: MarketIntelligenceSnapshot) -> MarketIntelligenceSnapshot:
        if not self.session:
            return snapshot
        existing = self.session.query(MarketIntelligenceSnapshotModel).filter(
            MarketIntelligenceSnapshotModel.id == snapshot.id
        ).first()
        if existing:
            existing.product_id = snapshot.product_id
            existing.unified_product_id = snapshot.unified_product_id
            existing.marketplace = snapshot.marketplace
            existing.category = snapshot.category
            existing.current_price = snapshot.current_price
            existing.historical_price = snapshot.historical_price
            existing.price_change_pct = snapshot.price_change_pct
            existing.currency = snapshot.currency
            existing.rating = snapshot.rating
            existing.review_count = snapshot.review_count
            existing.availability = snapshot.availability
            existing.market_score = snapshot.market_score
            existing.market_score_breakdown = snapshot.market_score_breakdown or {}
            existing.demand_score = snapshot.demand_score
            existing.demand_level = snapshot.demand_level
            existing.trend_velocity = snapshot.trend_velocity
            existing.growth_7d = snapshot.growth_7d
            existing.growth_30d = snapshot.growth_30d
            existing.viral_score = snapshot.viral_score
            existing.viral_level = snapshot.viral_level
            existing.opportunity_score = snapshot.opportunity_score
            existing.opportunity_level = snapshot.opportunity_level
            existing.social_mentions_count = snapshot.social_mentions_count
            existing.social_total_views = snapshot.social_total_views
            existing.social_total_engagement = snapshot.social_total_engagement
            existing.confidence_score = snapshot.confidence_score
            existing.data_quality_score = snapshot.data_quality_score
            existing.source_provenance = snapshot.source_provenance
            existing.ai_summary = snapshot.ai_summary
            existing.calculated_at = snapshot.calculated_at
        else:
            m = MarketIntelligenceSnapshotModel(
                id=snapshot.id,
                product_id=snapshot.product_id,
                unified_product_id=snapshot.unified_product_id,
                marketplace=snapshot.marketplace,
                category=snapshot.category,
                current_price=snapshot.current_price,
                historical_price=snapshot.historical_price,
                price_change_pct=snapshot.price_change_pct,
                currency=snapshot.currency,
                rating=snapshot.rating,
                review_count=snapshot.review_count,
                availability=snapshot.availability,
                market_score=snapshot.market_score,
                market_score_breakdown=snapshot.market_score_breakdown or {},
                demand_score=snapshot.demand_score,
                demand_level=snapshot.demand_level,
                trend_velocity=snapshot.trend_velocity,
                growth_7d=snapshot.growth_7d,
                growth_30d=snapshot.growth_30d,
                viral_score=snapshot.viral_score,
                viral_level=snapshot.viral_level,
                opportunity_score=snapshot.opportunity_score,
                opportunity_level=snapshot.opportunity_level,
                social_mentions_count=snapshot.social_mentions_count,
                social_total_views=snapshot.social_total_views,
                social_total_engagement=snapshot.social_total_engagement,
                confidence_score=snapshot.confidence_score,
                data_quality_score=snapshot.data_quality_score,
                source_provenance=snapshot.source_provenance,
                ai_summary=snapshot.ai_summary,
                calculated_at=snapshot.calculated_at,
                created_at=snapshot.created_at
            )
            self.session.add(m)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return snapshot

    def get_latest_snapshot(self, product_id: str, marketplace: Optional[str] = None) -> Optional[MarketIntelligenceSnapshot]:
        if not self.session:
            return None
        q = self.session.query(MarketIntelligenceSnapshotModel).filter(
            MarketIntelligenceSnapshotModel.product_id == product_id
        )
        if marketplace and marketplace.lower() != "all":
            q = q.filter(MarketIntelligenceSnapshotModel.marketplace.ilike(marketplace))
        m = q.order_by(MarketIntelligenceSnapshotModel.calculated_at.desc()).first()
        return self._snapshot_to_domain(m) if m else None

    def list_snapshots(
        self,
        product_id: Optional[str] = None,
        marketplace: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[MarketIntelligenceSnapshot]:
        if not self.session:
            return []
        q = self.session.query(MarketIntelligenceSnapshotModel)
        if product_id:
            q = q.filter(MarketIntelligenceSnapshotModel.product_id == product_id)
        if marketplace and marketplace.lower() != "all":
            q = q.filter(MarketIntelligenceSnapshotModel.marketplace.ilike(marketplace))
        items = q.order_by(MarketIntelligenceSnapshotModel.calculated_at.desc()).offset(offset).limit(limit).all()
        return [self._snapshot_to_domain(m) for m in items]

    def save_social_signal(self, signal: SocialSignal) -> SocialSignal:
        if not self.session:
            return signal
        existing = self.session.query(SocialSignalModel).filter(SocialSignalModel.id == signal.id).first()
        if existing:
            existing.platform = signal.platform
            existing.external_id = signal.external_id
            existing.content_title = signal.content_title
            existing.content_url = signal.content_url or ""
            existing.author_name = signal.author_name
            existing.views = signal.views
            existing.likes = signal.likes
            existing.comments = signal.comments
            existing.shares = signal.shares
            existing.engagement_rate = signal.engagement_rate
            existing.matched_product_id = signal.matched_product_id
            existing.matched_unified_id = signal.matched_unified_id
            existing.match_confidence = signal.match_confidence
            existing.observed_at = signal.observed_at
            existing.raw_metadata = signal.raw_metadata or {}
        else:
            m = SocialSignalModel(
                id=signal.id,
                platform=signal.platform,
                external_id=signal.external_id,
                content_title=signal.content_title,
                content_url=signal.content_url or "",
                author_name=signal.author_name,
                views=signal.views,
                likes=signal.likes,
                comments=signal.comments,
                shares=signal.shares,
                engagement_rate=signal.engagement_rate,
                matched_product_id=signal.matched_product_id,
                matched_unified_id=signal.matched_unified_id,
                match_confidence=signal.match_confidence,
                observed_at=signal.observed_at,
                raw_metadata=signal.raw_metadata or {},
                created_at=signal.created_at
            )
            self.session.add(m)
        self.session.commit()
        return signal

    def list_social_signals(
        self,
        platform: Optional[str] = None,
        product_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[SocialSignal]:
        if not self.session:
            return []
        q = self.session.query(SocialSignalModel)
        if platform and platform.lower() != "all":
            q = q.filter(SocialSignalModel.platform.ilike(platform))
        if product_id:
            q = q.filter(
                (SocialSignalModel.matched_product_id == product_id) |
                (SocialSignalModel.matched_unified_id == product_id)
            )
        items = q.order_by(SocialSignalModel.observed_at.desc()).offset(offset).limit(limit).all()
        return [self._social_to_domain(m) for m in items]

    def clear(self):
        if self.session:
            self.session.query(MarketIntelligenceSnapshotModel).delete()
            self.session.query(SocialSignalModel).delete()
            self.session.commit()



