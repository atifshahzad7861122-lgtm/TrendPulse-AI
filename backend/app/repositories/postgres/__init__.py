from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, func

from backend.app.models.domain import (
    User, Workspace, WorkspaceMember, UserSession, EmailVerification, PasswordResetToken, LoginEvent,
    Product, Category, PlatformMetrics, Alert, Notification, Report, DataSource, UserSettings,
    SubscriptionPlan, UserSubscription, CreditAccount, CreditTransaction, CreditUsage
)
from backend.app.repositories.base import (
    UserRepository, WorkspaceRepository, AuthPersistenceRepository, SubscriptionRepository, CreditRepository,
    ProductRepository, CategoryRepository, PlatformRepository, WatchlistRepository, AlertRepository,
    NotificationRepository, ReportRepository, DataSourceRepository, SettingsRepository
)
from backend.app.db.models import (
    UserModel, WorkspaceModel, WorkspaceMemberModel, UserSessionModel, EmailVerificationModel,
    PasswordResetTokenModel, LoginEventModel, UserSettingsModel, ProductModel, CategoryModel,
    PlatformModel, WatchlistModel, AlertModel, NotificationModel, ReportModel, DataSourceModel, SettingsModel,
    SubscriptionPlanModel, UserSubscriptionModel, CreditAccountModel, CreditTransactionModel, CreditUsageModel
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
        return Report(
            id=m.id,
            title=m.title,
            template=m.template,
            time_range=m.time_range,
            status=m.status,
            download_url=m.download_url,
            file_size=m.file_size,
            category_focus=m.category_focus,
            data_snapshot=m.data_snapshot or {},
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
        m = ReportModel(
            id=report.id,
            title=report.title,
            template=report.template,
            time_range=report.time_range,
            status=report.status,
            download_url=report.download_url,
            file_size=report.file_size,
            category_focus=report.category_focus,
            data_snapshot=report.data_snapshot,
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
            m.download_url = report.download_url
            m.data_snapshot = report.data_snapshot
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

