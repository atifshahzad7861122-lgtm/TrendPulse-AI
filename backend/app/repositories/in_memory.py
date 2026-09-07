import os
import json
import threading
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple
from backend.app.core.security import get_password_hash
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
    PublicDataQualityItem, PublicDataQualityStatsResponse,
    TaxonomyCategory, ProductTaxonomyAssignment, ProductTaxonomyCandidate,
    TrendObservation, TrendSignal, TrendSignalCandidate, TrendDetectionAudit, ProductTrendSummary, AgentTrendDetectionStats,
    AnomalyObservation, AnomalyDetection, AnomalyCandidate, AnomalyDetectionAudit, ProductAnomalySummary, AgentAnomalyDetectionStats,
    ProductRecommendation, RecommendationCandidate, RecommendationInteraction, RecommendationAudit, RecommendationScoreBreakdown, ProductRecommendationSummary, AgentRecommendationStats,
    MarketOpportunity, MarketOpportunityCandidate, MarketOpportunityAudit, MarketOpportunityScoreBreakdown, MarketOpportunitySummary, AgentMarketOpportunityStats,
    ScraperCrawlJob, RawScrapedPayload, ScraperMarketplaceHealth,
    MarketIntelligenceSnapshot, SocialSignal
)

from backend.app.repositories.base import (
    UserRepository, WorkspaceRepository, AuthPersistenceRepository, SubscriptionRepository, CreditRepository,
    ProductRepository, CategoryRepository, PlatformRepository, WatchlistRepository, AlertRepository,
    NotificationRepository, ReportRepository, DataSourceRepository, SettingsRepository,
    MarketplaceProductRepository, ShopifyRepository, UnifiedProductRepository, LLMUsageRepository,
    DataQualityRepository, TaxonomyRepository, TrendDetectionRepository, AnomalyDetectionRepository,
    RecommendationRepository, MarketOpportunityRepository, ScraperRepository,
    MarketIntelligenceRepository
)
from backend.app.domain.taxonomy import CENTRAL_TAXONOMY_TREE, INITIAL_TOP_LEVEL_CATEGORIES, generate_slug




class InMemoryUserRepository(UserRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._users: Dict[str, User] = {}
        # Preseed a default demo user
        demo_user = User(
            id="usr_demo_101",
            email="demo@trendpulse.ai",
            full_name="Alex Vance",
            hashed_password=get_password_hash("Password123!"),
            is_verified=True,
            workspace_id="ws_demo_101",
            role="Lead Market Strategist",
            avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80"
        )
        self._users[demo_user.id] = demo_user

    def get_by_id(self, user_id: str) -> Optional[User]:
        with self._lock:
            return self._users.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        with self._lock:
            for u in self._users.values():
                if u.email.lower() == email.lower():
                    return u
            return None

    def get_by_verification_token(self, token: str) -> Optional[User]:
        with self._lock:
            for u in self._users.values():
                if u.verification_token == token:
                    return u
            return None

    def get_by_reset_token(self, token: str) -> Optional[User]:
        with self._lock:
            for u in self._users.values():
                if u.reset_token == token:
                    return u
            return None

    def create(self, user: User) -> User:
        with self._lock:
            self._users[user.id] = user
            return user

    def update(self, user: User) -> User:
        with self._lock:
            self._users[user.id] = user
            return user

    def delete(self, user_id: str) -> bool:
        with self._lock:
            if user_id in self._users:
                del self._users[user_id]
                return True
            return False

class InMemoryWorkspaceRepository(WorkspaceRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._workspaces: Dict[str, Workspace] = {}
        self._members: Dict[str, List[WorkspaceMember]] = {}
        demo_ws = Workspace(
            id="ws_demo_101",
            name="Apex Intelligence Labs",
            industry="E-commerce & Consumer Tech",
            use_case="Trend Prediction & Competitor Arbitrage",
            currency="USD",
            default_dashboard="signals",
            connected_sources=["daraz", "tiktok", "instagram"],
            is_setup_complete=True,
            owner_id="usr_demo_101"
        )
        self._workspaces[demo_ws.id] = demo_ws
        self._members[demo_ws.id] = [
            WorkspaceMember(
                id="wsm_demo_101",
                workspace_id=demo_ws.id,
                user_id="usr_demo_101",
                role="Administrator"
            )
        ]

    def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        with self._lock:
            return self._workspaces.get(workspace_id)

    def get_by_owner_id(self, owner_id: str) -> Optional[Workspace]:
        with self._lock:
            for ws in self._workspaces.values():
                if ws.owner_id == owner_id:
                    return ws
            return None

    def create(self, workspace: Workspace) -> Workspace:
        with self._lock:
            self._workspaces[workspace.id] = workspace
            if workspace.id not in self._members:
                self._members[workspace.id] = []
            return workspace

    def update(self, workspace: Workspace) -> Workspace:
        with self._lock:
            self._workspaces[workspace.id] = workspace
            return workspace

    def add_member(self, member: WorkspaceMember) -> WorkspaceMember:
        with self._lock:
            if member.workspace_id not in self._members:
                self._members[member.workspace_id] = []
            self._members[member.workspace_id].append(member)
            return member

    def get_members(self, workspace_id: str) -> List[WorkspaceMember]:
        with self._lock:
            return list(self._members.get(workspace_id, []))

    def delete(self, workspace_id: str) -> bool:
        with self._lock:
            if workspace_id in self._workspaces:
                del self._workspaces[workspace_id]
                self._members.pop(workspace_id, None)
                return True
            return False

class InMemoryAuthPersistenceRepository(AuthPersistenceRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: Dict[str, UserSession] = {}  # token_hash -> session
        self._email_verifications: Dict[str, EmailVerification] = {}  # token -> record
        self._password_resets: Dict[str, PasswordResetToken] = {}  # token -> record
        self._login_events: List[LoginEvent] = []

    def create_session(self, session: UserSession) -> UserSession:
        with self._lock:
            self._sessions[session.token_hash] = session
            return session

    def get_session(self, token_hash: str) -> Optional[UserSession]:
        with self._lock:
            return self._sessions.get(token_hash)

    def revoke_session(self, token_hash: str) -> bool:
        with self._lock:
            if token_hash in self._sessions:
                s = self._sessions[token_hash]
                self._sessions[token_hash] = s.model_copy(update={"is_revoked": True})
                return True
            return False

    def revoke_all_user_sessions(self, user_id: str) -> int:
        with self._lock:
            count = 0
            for th, s in list(self._sessions.items()):
                if s.user_id == user_id and not s.is_revoked:
                    self._sessions[th] = s.model_copy(update={"is_revoked": True})
                    count += 1
            return count

    def create_email_verification(self, verification: EmailVerification) -> EmailVerification:
        with self._lock:
            self._email_verifications[verification.token] = verification
            return verification

    def get_email_verification(self, token: str) -> Optional[EmailVerification]:
        with self._lock:
            return self._email_verifications.get(token)

    def mark_email_verification_used(self, token: str) -> bool:
        with self._lock:
            if token in self._email_verifications:
                v = self._email_verifications[token]
                self._email_verifications[token] = v.model_copy(update={"used_at": datetime.now(timezone.utc)})
                return True
            return False

    def invalidate_user_verifications(self, user_id: str) -> int:
        with self._lock:
            count = 0
            now = datetime.now(timezone.utc)
            for token, v in list(self._email_verifications.items()):
                if v.user_id == user_id and v.used_at is None:
                    self._email_verifications[token] = v.model_copy(update={"used_at": now})
                    count += 1
            return count

    def create_password_reset_token(self, reset_token: PasswordResetToken) -> PasswordResetToken:
        with self._lock:
            self._password_resets[reset_token.token] = reset_token
            return reset_token

    def get_password_reset_token(self, token: str) -> Optional[PasswordResetToken]:
        with self._lock:
            return self._password_resets.get(token)

    def mark_password_reset_token_used(self, token: str) -> bool:
        with self._lock:
            if token in self._password_resets:
                r = self._password_resets[token]
                self._password_resets[token] = r.model_copy(update={"used_at": datetime.now(timezone.utc)})
                return True
            return False

    def record_login_event(self, event: LoginEvent) -> LoginEvent:
        with self._lock:
            self._login_events.append(event)
            return event

    def list_login_events(self, user_id: Optional[str] = None, email: Optional[str] = None) -> List[LoginEvent]:
        with self._lock:
            events = list(self._login_events)
            if user_id:
                events = [e for e in events if e.user_id == user_id]
            if email:
                events = [e for e in events if e.email.lower() == email.lower()]
            return events

class InMemoryProductRepository(ProductRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._products: Dict[str, Product] = {}
        self._seed_products()

    def _seed_products(self):
        now = datetime.now(timezone.utc)
        items = [
            Product(
                id="prod_01",
                name="HydroGlow Thermal Lip Serum",
                category="Beauty & Personal Care",
                sub_category="Skincare Cosmetics",
                trend_score=96.4,
                growth_rate=340.5,
                volume=184200,
                velocity_label="Explosive",
                status="Active",
                price_range="$18.00 - $28.00",
                primary_platform="TikTok",
                platforms=["TikTok", "Instagram", "Daraz"],
                platform_shares={"TikTok": 58.0, "Instagram": 28.0, "Daraz": 14.0},
                historical_scores=[
                    {"date": (now - timedelta(days=6)).strftime("%b %d"), "score": 68.2, "volume": 84000},
                    {"date": (now - timedelta(days=5)).strftime("%b %d"), "score": 74.5, "volume": 98000},
                    {"date": (now - timedelta(days=4)).strftime("%b %d"), "score": 81.0, "volume": 120000},
                    {"date": (now - timedelta(days=3)).strftime("%b %d"), "score": 88.6, "volume": 145000},
                    {"date": (now - timedelta(days=2)).strftime("%b %d"), "score": 92.1, "volume": 162000},
                    {"date": (now - timedelta(days=1)).strftime("%b %d"), "score": 94.8, "volume": 178000},
                    {"date": now.strftime("%b %d"), "score": 96.4, "volume": 184200},
                ],
                historical_prices=[
                    {"date": "Jan", "price": 24.0},
                    {"date": "Feb", "price": 22.5},
                    {"date": "Mar", "price": 26.0},
                    {"date": "Apr", "price": 25.0},
                    {"date": "May", "price": 28.0},
                ],
                ai_summary="Rapid viral adoption triggered by sensory color-shift videos. High repeat purchase intent detected across Gen Z demographics with low localized competitor saturation on regional marketplaces.",
                signals_count=1420,
                sentiment_score=0.92,
                image_url="https://images.unsplash.com/photo-1586495777744-4413f21062fa?w=400&auto=format&fit=crop&q=80",
                tags=["Viral Beauty", "Thermal Active", "High Margin", "TikTok Trending"],
                is_watchlisted=True
            ),
            Product(
                id="prod_02",
                name="TitanFlex Modular Running Vest",
                category="Sports & Outdoor",
                sub_category="Athletic Gear",
                trend_score=94.2,
                growth_rate=218.0,
                volume=129500,
                velocity_label="Breakout",
                status="Active",
                price_range="$34.00 - $55.00",
                primary_platform="YouTube",
                platforms=["YouTube", "TikTok", "Instagram", "Facebook"],
                platform_shares={"YouTube": 42.0, "TikTok": 31.0, "Instagram": 19.0, "Facebook": 8.0},
                historical_scores=[
                    {"date": (now - timedelta(days=6)).strftime("%b %d"), "score": 62.0, "volume": 52000},
                    {"date": (now - timedelta(days=5)).strftime("%b %d"), "score": 69.4, "volume": 68000},
                    {"date": (now - timedelta(days=4)).strftime("%b %d"), "score": 76.8, "volume": 84000},
                    {"date": (now - timedelta(days=3)).strftime("%b %d"), "score": 83.2, "volume": 99000},
                    {"date": (now - timedelta(days=2)).strftime("%b %d"), "score": 89.0, "volume": 114000},
                    {"date": (now - timedelta(days=1)).strftime("%b %d"), "score": 92.5, "volume": 124000},
                    {"date": now.strftime("%b %d"), "score": 94.2, "volume": 129500},
                ],
                historical_prices=[
                    {"date": "Jan", "price": 45.0},
                    {"date": "Feb", "price": 42.0},
                    {"date": "Mar", "price": 48.0},
                    {"date": "Apr", "price": 50.0},
                    {"date": "May", "price": 52.0},
                ],
                ai_summary="Run-club culture and marathon prep content on YouTube and TikTok are driving unprecedented demand for minimalist, ergonomic hydration hydration vests.",
                signals_count=980,
                sentiment_score=0.88,
                image_url="https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=400&auto=format&fit=crop&q=80",
                tags=["RunClub", "Ergonomic Gear", "Fitness Surge", "High Retention"],
                is_watchlisted=True
            ),
            Product(
                id="prod_03",
                name="MagSnap 3-in-1 Foldable Stand",
                category="Consumer Electronics",
                sub_category="Mobile Accessories",
                trend_score=91.8,
                growth_rate=185.4,
                volume=245000,
                velocity_label="Surging",
                status="Active",
                price_range="$22.00 - $39.00",
                primary_platform="Daraz",
                platforms=["Daraz", "TikTok", "YouTube"],
                platform_shares={"Daraz": 46.0, "TikTok": 34.0, "YouTube": 20.0},
                historical_scores=[
                    {"date": (now - timedelta(days=6)).strftime("%b %d"), "score": 75.0, "volume": 180000},
                    {"date": (now - timedelta(days=5)).strftime("%b %d"), "score": 78.5, "volume": 195000},
                    {"date": (now - timedelta(days=4)).strftime("%b %d"), "score": 82.0, "volume": 210000},
                    {"date": (now - timedelta(days=3)).strftime("%b %d"), "score": 85.4, "volume": 225000},
                    {"date": (now - timedelta(days=2)).strftime("%b %d"), "score": 88.0, "volume": 235000},
                    {"date": (now - timedelta(days=1)).strftime("%b %d"), "score": 90.2, "volume": 240000},
                    {"date": now.strftime("%b %d"), "score": 91.8, "volume": 245000},
                ],
                historical_prices=[
                    {"date": "Jan", "price": 28.0},
                    {"date": "Feb", "price": 26.0},
                    {"date": "Mar", "price": 29.0},
                    {"date": "Apr", "price": 32.0},
                    {"date": "May", "price": 35.0},
                ],
                ai_summary="Travel season demand acceleration coupled with desk aesthetic creators driving strong conversion rates across online marketplaces.",
                signals_count=1840,
                sentiment_score=0.85,
                image_url="https://images.unsplash.com/photo-1586105251261-72a756497a11?w=400&auto=format&fit=crop&q=80",
                tags=["Desk Setup", "MagSafe", "Fast Turnover", "Travel Essential"],
                is_watchlisted=False
            ),
            Product(
                id="prod_04",
                name="Ceramic Infused Matcha Whisk & Bowl Set",
                category="Home & Kitchen",
                sub_category="Specialty Beverage",
                trend_score=89.5,
                growth_rate=162.0,
                volume=98400,
                velocity_label="Surging",
                status="Active",
                price_range="$28.00 - $44.00",
                primary_platform="Instagram",
                platforms=["Instagram", "TikTok", "YouTube"],
                platform_shares={"Instagram": 52.0, "TikTok": 36.0, "YouTube": 12.0},
                historical_scores=[
                    {"date": (now - timedelta(days=6)).strftime("%b %d"), "score": 71.0, "volume": 64000},
                    {"date": (now - timedelta(days=5)).strftime("%b %d"), "score": 75.0, "volume": 72000},
                    {"date": (now - timedelta(days=4)).strftime("%b %d"), "score": 79.5, "volume": 81000},
                    {"date": (now - timedelta(days=3)).strftime("%b %d"), "score": 83.0, "volume": 89000},
                    {"date": (now - timedelta(days=2)).strftime("%b %d"), "score": 86.2, "volume": 93000},
                    {"date": (now - timedelta(days=1)).strftime("%b %d"), "score": 88.0, "volume": 96000},
                    {"date": now.strftime("%b %d"), "score": 89.5, "volume": 98400},
                ],
                historical_prices=[
                    {"date": "Jan", "price": 32.0},
                    {"date": "Feb", "price": 32.0},
                    {"date": "Mar", "price": 35.0},
                    {"date": "Apr", "price": 38.0},
                    {"date": "May", "price": 40.0},
                ],
                ai_summary="Rising wellness beverage trends replacing traditional coffee routines among urban professionals. High aesthetic value encourages social sharing.",
                signals_count=760,
                sentiment_score=0.91,
                image_url="https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=400&auto=format&fit=crop&q=80",
                tags=["Wellness Trend", "Matcha Craze", "Aesthetic Home", "Organic Demand"],
                is_watchlisted=False
            ),
            Product(
                id="prod_05",
                name="AuraGlow Ambient Sunset Projection Lamp",
                category="Home & Living",
                sub_category="Lighting & Decor",
                trend_score=87.2,
                growth_rate=145.8,
                volume=156000,
                velocity_label="Steady",
                status="Active",
                price_range="$15.00 - $26.00",
                primary_platform="TikTok",
                platforms=["TikTok", "Instagram", "Daraz"],
                platform_shares={"TikTok": 48.0, "Instagram": 32.0, "Daraz": 20.0},
                historical_scores=[
                    {"date": (now - timedelta(days=6)).strftime("%b %d"), "score": 76.0, "volume": 120000},
                    {"date": (now - timedelta(days=5)).strftime("%b %d"), "score": 79.0, "volume": 130000},
                    {"date": (now - timedelta(days=4)).strftime("%b %d"), "score": 81.5, "volume": 138000},
                    {"date": (now - timedelta(days=3)).strftime("%b %d"), "score": 83.8, "volume": 144000},
                    {"date": (now - timedelta(days=2)).strftime("%b %d"), "score": 85.2, "volume": 149000},
                    {"date": (now - timedelta(days=1)).strftime("%b %d"), "score": 86.5, "volume": 153000},
                    {"date": now.strftime("%b %d"), "score": 87.2, "volume": 156000},
                ],
                historical_prices=[
                    {"date": "Jan", "price": 20.0},
                    {"date": "Feb", "price": 19.0},
                    {"date": "Mar", "price": 22.0},
                    {"date": "Apr", "price": 22.0},
                    {"date": "May", "price": 24.0},
                ],
                ai_summary="Consistent mood-lighting trend driven by lifestyle content creators and dormitory decor season.",
                signals_count=1120,
                sentiment_score=0.82,
                image_url="https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=400&auto=format&fit=crop&q=80",
                tags=["Ambient Light", "TikTok Made Me Buy It", "Room Decor"],
                is_watchlisted=False
            ),
            Product(
                id="prod_06",
                name="PureAir Ionizing Portable Neck Fan",
                category="Consumer Electronics",
                sub_category="Personal Climate",
                trend_score=85.0,
                growth_rate=128.4,
                volume=112000,
                velocity_label="Steady",
                status="Active",
                price_range="$19.00 - $32.00",
                primary_platform="Daraz",
                platforms=["Daraz", "Facebook", "TikTok"],
                platform_shares={"Daraz": 50.0, "TikTok": 30.0, "Facebook": 20.0},
                historical_scores=[
                    {"date": (now - timedelta(days=6)).strftime("%b %d"), "score": 72.0, "volume": 85000},
                    {"date": (now - timedelta(days=5)).strftime("%b %d"), "score": 75.0, "volume": 92000},
                    {"date": (now - timedelta(days=4)).strftime("%b %d"), "score": 78.0, "volume": 98000},
                    {"date": (now - timedelta(days=3)).strftime("%b %d"), "score": 80.5, "volume": 103000},
                    {"date": (now - timedelta(days=2)).strftime("%b %d"), "score": 82.8, "volume": 107000},
                    {"date": (now - timedelta(days=1)).strftime("%b %d"), "score": 84.0, "volume": 110000},
                    {"date": now.strftime("%b %d"), "score": 85.0, "volume": 112000},
                ],
                historical_prices=[
                    {"date": "Jan", "price": 22.0},
                    {"date": "Feb", "price": 22.0},
                    {"date": "Mar", "price": 25.0},
                    {"date": "Apr", "price": 28.0},
                    {"date": "May", "price": 30.0},
                ],
                ai_summary="Seasonal heatwave anticipation causing early spike in commuter cooling gadgets across South Asian markets.",
                signals_count=890,
                sentiment_score=0.79,
                image_url="https://images.unsplash.com/photo-1590486803833-1c5dc8ddd4c8?w=400&auto=format&fit=crop&q=80",
                tags=["Summer Surge", "Commute Gear", "High Velocity"],
                is_watchlisted=False
            )
        ]
        for p in items:
            self._products[p.id] = p

    def get_by_id(self, product_id: str) -> Optional[Product]:
        with self._lock:
            return self._products.get(product_id)

    def list(self, category: Optional[str] = None, platform: Optional[str] = None, search: Optional[str] = None, sort_by: Optional[str] = None) -> List[Product]:
        with self._lock:
            results = list(self._products.values())
            if category and category.lower() != "all":
                results = [p for p in results if p.category.lower() == category.lower()]
            if platform and platform.lower() != "all":
                results = [p for p in results if platform.lower() in [pl.lower() for pl in p.platforms]]
            if search:
                query = search.lower()
                results = [p for p in results if query in p.name.lower() or query in p.category.lower() or any(query in tag.lower() for tag in p.tags)]
            
            if sort_by == "growth":
                results.sort(key=lambda x: x.growth_rate, reverse=True)
            elif sort_by == "volume":
                results.sort(key=lambda x: x.volume, reverse=True)
            elif sort_by == "sentiment":
                results.sort(key=lambda x: x.sentiment_score, reverse=True)
            else:
                # default trend score
                results.sort(key=lambda x: x.trend_score, reverse=True)
            return results

    def update(self, product: Product) -> Product:
        with self._lock:
            self._products[product.id] = product
            return product

class InMemoryCategoryRepository(CategoryRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._categories: Dict[str, Category] = {}
        now = datetime.now(timezone.utc)
        cats = [
            Category(
                id="cat_beauty",
                name="Beauty & Personal Care",
                slug="beauty",
                product_count=0,
                avg_trend_score=0.0,
                growth_rate=0.0,
                velocity_label="Steady",
                top_platforms=[],
                description="Skincare, color cosmetics, hair wellness, and clean beauty formulas."
            ),
            Category(
                id="cat_sports",
                name="Sports & Outdoor",
                slug="sports",
                product_count=0,
                avg_trend_score=0.0,
                growth_rate=0.0,
                velocity_label="Steady",
                top_platforms=[],
                description="Running apparel, hydration packs, recovery tech, and outdoor gear."
            ),
            Category(
                id="cat_electronics",
                name="Consumer Electronics",
                slug="electronics",
                product_count=0,
                avg_trend_score=0.0,
                growth_rate=0.0,
                velocity_label="Steady",
                top_platforms=[],
                description="Smart wearables, mobile MagSafe accessories, and desktop audio."
            ),
            Category(
                id="cat_home",
                name="Home & Living",
                slug="home-living",
                product_count=0,
                avg_trend_score=0.0,
                growth_rate=0.0,
                velocity_label="Steady",
                top_platforms=[],
                description="Ceremonial beverage prep, ergonomic home goods, and kitchenware."
            ),
            Category(
                id="cat_fashion",
                name="Fashion & Apparel",
                slug="fashion",
                product_count=0,
                avg_trend_score=0.0,
                growth_rate=0.0,
                velocity_label="Steady",
                top_platforms=[],
                description="Functional streetwear, activewear sets, and viral accessories."
            )
        ]
        for c in cats:
            self._categories[c.id] = c

    def list(self) -> List[Category]:
        with self._lock:
            return list(self._categories.values())

    def get_by_id(self, category_id: str) -> Optional[Category]:
        with self._lock:
            for c in self._categories.values():
                if c.id == category_id or c.slug == category_id:
                    return c
            return None

class InMemoryPlatformRepository(PlatformRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._platforms: Dict[str, PlatformMetrics] = {}
        now = datetime.now(timezone.utc)
        platforms = [
            PlatformMetrics(
                id="plt_youtube",
                name="YouTube",
                slug="youtube",
                icon="smart_display",
                total_signals=0,
                active_trends=0,
                velocity_growth=0.0,
                market_share=0.0,
                status="Connected",
                provenance="live_ingested_signals",
                observation_count=0,
                recent_spikes=[]
            ),
            PlatformMetrics(
                id="plt_daraz",
                name="Daraz",
                slug="daraz",
                icon="shopping_bag",
                total_signals=0,
                active_trends=0,
                velocity_growth=0.0,
                market_share=0.0,
                status="Connected",
                provenance="persisted_marketplace_observations",
                observation_count=0,
                recent_spikes=[]
            ),
            PlatformMetrics(
                id="plt_tiktok",
                name="TikTok",
                slug="tiktok",
                icon="tiktok",
                total_signals=0,
                active_trends=0,
                velocity_growth=0.0,
                market_share=0.0,
                status="Coming Soon",
                provenance="none",
                observation_count=0,
                recent_spikes=[]
            ),
            PlatformMetrics(
                id="plt_instagram",
                name="Instagram",
                slug="instagram",
                icon="photo_camera",
                total_signals=0,
                active_trends=0,
                velocity_growth=0.0,
                market_share=0.0,
                status="Coming Soon",
                provenance="none",
                observation_count=0,
                recent_spikes=[]
            ),
            PlatformMetrics(
                id="plt_facebook",
                name="Facebook",
                slug="facebook",
                icon="group",
                total_signals=0,
                active_trends=0,
                velocity_growth=0.0,
                market_share=0.0,
                status="Coming Soon",
                provenance="none",
                observation_count=0,
                recent_spikes=[]
            )
        ]
        for p in platforms:
            self._platforms[p.slug] = p

    def list(self) -> List[PlatformMetrics]:
        with self._lock:
            return list(self._platforms.values())

    def get_by_slug(self, slug: str) -> Optional[PlatformMetrics]:
        with self._lock:
            return self._platforms.get(slug.lower())

class InMemoryWatchlistRepository(WatchlistRepository):
    def __init__(self):
        self._lock = threading.Lock()
        # map user_id -> set of product_ids
        self._watchlists: Dict[str, set] = {
            "usr_demo_101": {"prod_01", "prod_02"}
        }

    def list_product_ids(self, user_id: str) -> List[str]:
        with self._lock:
            return list(self._watchlists.get(user_id, set()))

    def add(self, user_id: str, product_id: str) -> bool:
        with self._lock:
            if user_id not in self._watchlists:
                self._watchlists[user_id] = set()
            self._watchlists[user_id].add(product_id)
            return True

    def remove(self, user_id: str, product_id: str) -> bool:
        with self._lock:
            if user_id in self._watchlists and product_id in self._watchlists[user_id]:
                self._watchlists[user_id].remove(product_id)
                return True
            return False

    def is_in_watchlist(self, user_id: str, product_id: str) -> bool:
        with self._lock:
            return product_id in self._watchlists.get(user_id, set())

class InMemoryAlertRepository(AlertRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._alerts: Dict[str, Alert] = {}
        now = datetime.now(timezone.utc)
        alerts = [
            Alert(
                id="alt_01",
                title="Explosive Velocity Surge Detected",
                description="HydroGlow Thermal Lip Serum crossed +340% velocity on TikTok in 48h. Regional Daraz inventory is rapidly depleting.",
                severity="Critical",
                category="Beauty & Personal Care",
                product_id="prod_01",
                product_name="HydroGlow Thermal Lip Serum",
                platform="TikTok",
                is_read=False,
                is_resolved=False,
                created_at=now - timedelta(hours=2)
            ),
            Alert(
                id="alt_02",
                title="Search Volume Spike Anomaly",
                description="TitanFlex Running Vest search volume expanded 3.2x WoW across regional sports sub-communities.",
                severity="Warning",
                category="Sports & Outdoor",
                product_id="prod_02",
                product_name="TitanFlex Modular Running Vest",
                platform="YouTube",
                is_read=False,
                is_resolved=False,
                created_at=now - timedelta(hours=6)
            ),
            Alert(
                id="alt_03",
                title="New Marketplace Competitor Entry",
                description="3 new merchant stores listed 3-in-1 Foldable Stands with 15% discount margins.",
                severity="Info",
                category="Consumer Electronics",
                product_id="prod_03",
                product_name="MagSnap 3-in-1 Foldable Stand",
                platform="Daraz",
                is_read=True,
                is_resolved=False,
                created_at=now - timedelta(days=1)
            )
        ]
        for a in alerts:
            self._alerts[a.id] = a

    def list(self, severity: Optional[str] = None, unread_only: bool = False) -> List[Alert]:
        with self._lock:
            results = list(self._alerts.values())
            if severity and severity.lower() != "all":
                results = [a for a in results if a.severity.lower() == severity.lower()]
            if unread_only:
                results = [a for a in results if not a.is_read]
            results.sort(key=lambda x: x.created_at, reverse=True)
            return results

    def get_by_id(self, alert_id: str) -> Optional[Alert]:
        with self._lock:
            return self._alerts.get(alert_id)

    def create(self, alert: Alert) -> Alert:
        with self._lock:
            self._alerts[alert.id] = alert
            return alert


    def mark_read(self, alert_id: str) -> Optional[Alert]:
        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert:
                alert.is_read = True
                return alert
            return None

    def resolve(self, alert_id: str) -> Optional[Alert]:
        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert:
                alert.is_resolved = True
                alert.is_read = True
                return alert
            return None

class InMemoryNotificationRepository(NotificationRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._notifications: Dict[str, Notification] = {}
        now = datetime.now(timezone.utc)
        items = [
            Notification(
                id="notif_01",
                title="Signal Velocity Spike",
                message="HydroGlow Thermal Lip Serum exceeded 95 score threshold.",
                type="alert",
                is_read=False,
                link="/products/prod_01",
                created_at=now - timedelta(minutes=45)
            ),
            Notification(
                id="notif_02",
                title="Weekly Intelligence Report Ready",
                message="Your Q2 Consumer Electronics & Beauty briefing is ready for export.",
                type="report",
                is_read=False,
                link="/reports/rep_01",
                created_at=now - timedelta(hours=4)
            ),
            Notification(
                id="notif_03",
                title="TikTok Source Synced",
                message="Successfully ingested 14,200 video engagement data points.",
                type="integration",
                is_read=True,
                link="/data-sources",
                created_at=now - timedelta(days=1)
            )
        ]
        for n in items:
            self._notifications[n.id] = n

    def list(self, unread_only: bool = False) -> List[Notification]:
        with self._lock:
            results = list(self._notifications.values())
            if unread_only:
                results = [n for n in results if not n.is_read]
            results.sort(key=lambda x: x.created_at, reverse=True)
            return results

    def mark_read(self, notification_id: str) -> Optional[Notification]:
        with self._lock:
            n = self._notifications.get(notification_id)
            if n:
                n.is_read = True
                return n
            return None

    def mark_all_read(self) -> int:
        with self._lock:
            count = 0
            for n in self._notifications.values():
                if not n.is_read:
                    n.is_read = True
                    count += 1
            return count

class InMemoryReportRepository(ReportRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._reports: Dict[str, Report] = {}

    def list(self) -> List[Report]:
        with self._lock:
            results = list(self._reports.values())
            results.sort(key=lambda x: x.created_at, reverse=True)
            return results

    def get_by_id(self, report_id: str) -> Optional[Report]:
        with self._lock:
            return self._reports.get(report_id)

    def create(self, report: Report) -> Report:
        with self._lock:
            self._reports[report.id] = report
            return report

    def update(self, report: Report) -> Report:
        with self._lock:
            self._reports[report.id] = report
            return report

class InMemoryDataSourceRepository(DataSourceRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._sources: Dict[str, DataSource] = {}
        now = datetime.now(timezone.utc)
        sources = [
            DataSource(
                id="src_youtube",
                name="YouTube Long-form & Shorts API",
                slug="youtube",
                icon="smart_display",
                description="Live video metadata, engagement velocity, and review sentiment via YouTube Data API v3.",
                status="Connected",
                last_sync=now - timedelta(minutes=10),
                sync_frequency="Real-time (API v3)",
                records_synced=290000,
                health_score=100
            ),
            DataSource(
                id="src_shopify",
                name="Shopify Multi-Provider Pool",
                slug="shopify",
                icon="shopping_cart",
                description="5-Tier Ordered Failover Pool (Scout, ShopScraper, Apps Spy, Xtracto, Bornoo) with auto-cooldown, recovery, and persistence.",
                status="Connected",
                last_sync=now - timedelta(minutes=5),
                sync_frequency="Real-time Failover",
                records_synced=142000,
                health_score=100
            ),
            DataSource(
                id="src_daraz",
                name="Daraz Marketplace Scraper",
                slug="daraz",
                icon="shopping_bag",
                description="Tracks real-time pricing, catalog variations, stock changes, and customer reviews via autonomous scraping and Open Platform API.",
                status="Connected",
                last_sync=now - timedelta(minutes=2),
                sync_frequency="On-demand Scraper",
                records_synced=0,
                health_score=100
            ),
            DataSource(
                id="src_tiktok",
                name="TikTok Social Intelligence",
                slug="tiktok",
                icon="tiktok",
                description="Monitors video engagement, hashtag velocity, and creator mentions (Real API Connector in Development).",
                status="Coming Soon",
                last_sync=None,
                sync_frequency="Not Connected",
                records_synced=0,
                health_score=0
            ),
            DataSource(
                id="src_instagram",
                name="Instagram Trends Graph",
                slug="instagram",
                icon="photo_camera",
                description="Ingests reels audio surges, lifestyle carousel trends, and brand tagging (Real API Connector in Development).",
                status="Coming Soon",
                last_sync=None,
                sync_frequency="Not Connected",
                records_synced=0,
                health_score=0
            ),
            DataSource(
                id="src_facebook",
                name="Facebook Marketplace & Groups",
                slug="facebook",
                icon="group",
                description="Monitors localized buying demand and peer-to-peer commerce listings (Real API Connector in Development).",
                status="Coming Soon",
                last_sync=None,
                sync_frequency="Not Connected",
                records_synced=0,
                health_score=0
            )
        ]
        for s in sources:
            self._sources[s.slug] = s

    def list(self) -> List[DataSource]:
        with self._lock:
            return list(self._sources.values())

    def get_by_slug(self, slug: str) -> Optional[DataSource]:
        with self._lock:
            return self._sources.get(slug.lower())

    def update_status(self, slug: str, status: str) -> Optional[DataSource]:
        with self._lock:
            s = self._sources.get(slug.lower())
            if s:
                s.status = status
                if status == "Connected":
                    s.last_sync = datetime.now(timezone.utc)
                    s.health_score = 98
                    s.records_synced = s.records_synced or 125000
                elif status == "Disconnected":
                    s.health_score = 0
                return s
            return None

    def update(self, data_source: DataSource) -> DataSource:
        with self._lock:
            self._sources[data_source.slug.lower()] = data_source
            return data_source

    def save(self, data_source: DataSource) -> DataSource:
        return self.update(data_source)

class InMemorySettingsRepository(SettingsRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._settings: Dict[str, UserSettings] = {}
        demo_settings = UserSettings(
            user_id="usr_demo_101",
            full_name="Alex Vance",
            email="demo@trendpulse.ai",
            avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
            role="Lead Market Strategist",
            company_name="Apex Intelligence Labs",
            timezone="UTC",
            currency="USD",
            email_notifications=True,
            alert_critical_only=False,
            weekly_digest=True,
            ai_model_preference="Qwen 2.5 Max (Simulated)",
            ai_confidence_threshold=85,
            auto_generate_reports=True,
            dark_mode=True,
            table_dense_view=False,
            live_ticker_enabled=True
        )
        self._settings[demo_settings.user_id] = demo_settings

    def get_by_user_id(self, user_id: str) -> UserSettings:
        with self._lock:
            if user_id in self._settings:
                return self._settings[user_id]
            # default
            default_st = UserSettings(
                user_id=user_id,
                full_name="User",
                email="user@trendpulse.ai"
            )
            self._settings[user_id] = default_st
            return default_st

    def update(self, settings: UserSettings) -> UserSettings:
        with self._lock:
            self._settings[settings.user_id] = settings
            return settings

class InMemorySubscriptionRepository(SubscriptionRepository):
    def __init__(self):
        self._lock = threading.RLock()
        self._plans: Dict[str, SubscriptionPlan] = {}
        self._user_subscriptions: Dict[str, UserSubscription] = {}
        self._seed_plans()

    def _seed_plans(self):
        now = datetime.now(timezone.utc)
        plans = [
            SubscriptionPlan(
                id="plan_free",
                name="Free",
                slug="free",
                description="Essential trend detection for emerging sellers",
                price=0.0,
                currency="USD",
                billing_interval="monthly",
                monthly_credits=100,
                is_active=True,
                features=["Standard Signals", "100 Monthly AI Credits", "Weekly Digest", "Basic Export"],
                limits={"max_alerts": 5, "report_limit": 3},
                created_at=now,
                updated_at=now
            ),
            SubscriptionPlan(
                id="plan_pro",
                name="Pro",
                slug="pro",
                description="Full market intelligence with automated alerts and predictions",
                price=49.0,
                currency="USD",
                billing_interval="monthly",
                monthly_credits=1000,
                is_active=True,
                features=["All Platforms & Signals", "1,000 Monthly AI Credits", "Real-time Alerts", "Multi-platform Sync", "Custom Reports"],
                limits={"max_alerts": 25, "report_limit": 20},
                created_at=now,
                updated_at=now
            ),
            SubscriptionPlan(
                id="plan_business",
                name="Business",
                slug="business",
                description="Advanced market synthesis for growing commerce enterprises",
                price=199.0,
                currency="USD",
                billing_interval="monthly",
                monthly_credits=5000,
                is_active=True,
                features=["5,000 Monthly AI Credits", "Predictive Analytics", "Unlimited Reports", "Priority Ingestion", "Dedicated Support"],
                limits={"max_alerts": 100, "report_limit": 100},
                created_at=now,
                updated_at=now
            ),
            SubscriptionPlan(
                id="plan_enterprise",
                name="Enterprise",
                slug="enterprise",
                description="Custom AI intelligence pipelines, maximum credits, and dedicated SLAs",
                price=599.0,
                currency="USD",
                billing_interval="monthly",
                monthly_credits=25000,
                is_active=True,
                features=["25,000 Monthly AI Credits", "Custom AI Models", "Full API Access", "Dedicated Infrastructure", "24/7 SLA"],
                limits={"max_alerts": 999, "report_limit": 999},
                created_at=now,
                updated_at=now
            )
        ]
        for p in plans:
            self._plans[p.id] = p

        # Preseed demo user subscription
        demo_sub = UserSubscription(
            id="sub_demo_101",
            user_id="usr_demo_101",
            plan_id="plan_pro",
            status="active",
            started_at=now - timedelta(days=15),
            current_period_start=now - timedelta(days=15),
            current_period_end=now + timedelta(days=15),
            created_at=now - timedelta(days=15),
            updated_at=now
        )
        self._user_subscriptions[demo_sub.user_id] = demo_sub

    def list_plans(self, active_only: bool = True) -> List[SubscriptionPlan]:
        with self._lock:
            if active_only:
                return [p for p in self._plans.values() if p.is_active]
            return list(self._plans.values())

    def get_plan_by_id(self, plan_id: str) -> Optional[SubscriptionPlan]:
        with self._lock:
            return self._plans.get(plan_id)

    def get_plan_by_slug(self, slug: str) -> Optional[SubscriptionPlan]:
        with self._lock:
            for p in self._plans.values():
                if p.slug.lower() == slug.lower():
                    return p
            return None

    def get_user_subscription(self, user_id: str) -> Optional[UserSubscription]:
        with self._lock:
            return self._user_subscriptions.get(user_id)

    def create_user_subscription(self, subscription: UserSubscription) -> UserSubscription:
        with self._lock:
            self._user_subscriptions[subscription.user_id] = subscription
            return subscription

    def update_user_subscription(self, subscription: UserSubscription) -> UserSubscription:
        with self._lock:
            subscription.updated_at = datetime.now(timezone.utc)
            self._user_subscriptions[subscription.user_id] = subscription
            return subscription

class InMemoryCreditRepository(CreditRepository):
    def __init__(self):
        self._lock = threading.RLock()
        self._accounts: Dict[str, CreditAccount] = {}
        self._transactions: List[CreditTransaction] = []
        self._usages: List[CreditUsage] = []
        self._seed_demo()

    def _seed_demo(self):
        now = datetime.now(timezone.utc)
        demo_account = CreditAccount(
            id="cacc_demo_101",
            user_id="usr_demo_101",
            current_balance=1000,
            lifetime_granted=1000,
            lifetime_used=0,
            created_at=now - timedelta(days=15),
            updated_at=now
        )
        self._accounts[demo_account.user_id] = demo_account
        self._transactions.append(
            CreditTransaction(
                id="tx_demo_init",
                credit_account_id=demo_account.id,
                user_id="usr_demo_101",
                amount=1000,
                transaction_type="subscription_allocation",
                balance_before=0,
                balance_after=1000,
                reference_type="subscription_period",
                reference_id="initial_grant",
                description="Initial Pro plan credit allocation",
                metadata_json={"plan": "Pro"},
                created_at=now - timedelta(days=15)
            )
        )

    def get_or_create_account(self, user_id: str) -> CreditAccount:
        with self._lock:
            if user_id in self._accounts:
                return self._accounts[user_id].model_copy()
            now = datetime.now(timezone.utc)
            new_acc = CreditAccount(
                id=f"cacc_{user_id.replace('usr_', '')}",
                user_id=user_id,
                current_balance=0,
                lifetime_granted=0,
                lifetime_used=0,
                created_at=now,
                updated_at=now
            )
            self._accounts[user_id] = new_acc
            return new_acc.model_copy()

    def get_account(self, user_id: str) -> Optional[CreditAccount]:
        with self._lock:
            acc = self._accounts.get(user_id)
            return acc.model_copy() if acc else None

    def update_account_balance(self, user_id: str, new_balance: int, delta_granted: int, delta_used: int) -> CreditAccount:
        with self._lock:
            if new_balance < 0:
                raise ValueError("Credit balance cannot become negative")
            acc = self._accounts.get(user_id)
            if not acc:
                acc = self.get_or_create_account(user_id)
            acc.current_balance = new_balance
            acc.lifetime_granted += delta_granted
            acc.lifetime_used += delta_used
            acc.updated_at = datetime.now(timezone.utc)
            self._accounts[user_id] = acc
            return acc.model_copy()

    def create_transaction(self, tx: CreditTransaction) -> CreditTransaction:
        with self._lock:
            self._transactions.append(tx)
            return tx.model_copy()

    def get_transaction_by_reference(self, user_id: str, reference_type: str, reference_id: str) -> Optional[CreditTransaction]:
        with self._lock:
            for tx in reversed(self._transactions):
                if tx.user_id == user_id and tx.reference_type == reference_type and tx.reference_id == reference_id:
                    return tx.model_copy()
            return None

    def list_transactions(self, user_id: str, limit: int = 50, offset: int = 0) -> List[CreditTransaction]:
        with self._lock:
            user_txs = [tx.model_copy() for tx in self._transactions if tx.user_id == user_id]
            user_txs.sort(key=lambda t: t.created_at, reverse=True)
            return user_txs[offset:offset + limit]

    def record_usage(self, usage: CreditUsage) -> CreditUsage:
        with self._lock:
            self._usages.append(usage)
            return usage.model_copy()

    def get_usage_by_reference(self, user_id: str, reference_type: str, reference_id: str) -> Optional[CreditUsage]:
        with self._lock:
            for u in reversed(self._usages):
                if u.user_id == user_id and u.reference_type == reference_type and u.reference_id == reference_id:
                    return u.model_copy()
            return None

    def list_usage(self, user_id: str, limit: int = 50, offset: int = 0) -> List[CreditUsage]:
        with self._lock:
            user_usages = [u.model_copy() for u in self._usages if u.user_id == user_id]
            user_usages.sort(key=lambda u: u.created_at, reverse=True)
            return user_usages[offset:offset + limit]

import json
import os

class InMemoryMarketplaceProductRepository(MarketplaceProductRepository):
    """
    In-Memory repository for real marketplace products with optional disk persistence
    so real market observations survive service restarts.
    """
    def __init__(self, storage_file: Optional[str] = None):
        self._lock = threading.Lock()
        self._products: Dict[str, MarketplaceProduct] = {}
        self._snapshots: List[ProductMarketSnapshot] = []
        self._auth_sessions: Dict[str, DarazAuthSession] = {}
        self._provider_health: Dict[str, DarazProviderHealth] = {}
        self._sellers: Dict[str, DarazSeller] = {}
        self._categories: Dict[str, DarazCategory] = {}
        self._reviews: Dict[str, DarazReview] = {}
        self._ingestion_runs: Dict[str, DarazIngestionRun] = {}
        self._telemetry: List[DarazApiTelemetry] = []
        self._quotas: Dict[str, DarazDailyQuota] = {}
        self._training_dataset: Dict[str, DarazTrainingDataset] = {}
        self._init_default_daraz_providers()
        
        # Default storage file path in backend/data or scratch
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        self._prod_storage_file = os.path.normpath(os.path.join(data_dir, "marketplace_products_store.json"))

        # Default storage file path in backend/data or scratch
        if storage_file:
            self._storage_file = storage_file if storage_file == ":memory:" else os.path.normpath(storage_file)
        else:
            self._storage_file = self._prod_storage_file

        self._load_from_disk()

    def _init_default_daraz_providers(self):
        now = datetime.now(timezone.utc)
        defaults = [
            ("daraz_official_open_platform", 1),
            ("parse_daraz_api", 2),
            ("daraz_direct_fallback", 3),
            ("database_cache", 4),
        ]
        for name, prio in defaults:
            self._provider_health[name] = DarazProviderHealth(
                id=f"prov_{name}",
                provider_name=name,
                priority=prio,
                enabled=True,
                status="healthy",
                consecutive_failures=0,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                rate_limited_requests=0,
                created_at=now,
                updated_at=now
            )

    def _get_key(self, platform: str, product_id: str) -> str:
        return f"{platform.lower()}:{str(product_id).strip()}"

    def is_test_session(self, session: DarazAuthSession) -> bool:
        token = (session.access_token or "").lower()
        sess_id = (session.id or "").lower()
        account = (session.account or "").lower()
        seller_id = (session.seller_id or "").lower()
        return (
            token.startswith("mock_") or token.startswith("test_") or token.startswith("fake_") or token.startswith("sentinel_") or
            sess_id.startswith("mock_") or sess_id.startswith("test_") or
            account.startswith("mock_") or account.startswith("seller_pk_") or
            seller_id.startswith("mock_") or seller_id.startswith("seller_pk_")
        )

    def is_testing_environment(self) -> bool:
        return bool(
            os.getenv("TESTING") == "true" or
            os.getenv("PYTEST_CURRENT_TEST") or
            getattr(settings, "ENVIRONMENT", "").lower() == "test"
        )

    def _load_from_disk(self):
        if not self._storage_file or self._storage_file == ":memory:" or not os.path.exists(self._storage_file):
            return
        is_prod = (self._storage_file == self._prod_storage_file)
        try:
            with open(self._storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for p_dict in data.get("products", []):
                    p = MarketplaceProduct(**p_dict)
                    key = self._get_key(p.platform, p.product_id)
                    self._products[key] = p
                for s_dict in data.get("snapshots", []):
                    self._snapshots.append(ProductMarketSnapshot(**s_dict))
                for a_dict in data.get("auth_sessions", []):
                    sess = DarazAuthSession(**a_dict)
                    if not is_prod or not self.is_test_session(sess):
                        self._auth_sessions[sess.id] = sess
                        if sess.seller_id:
                            self._auth_sessions[sess.seller_id] = sess
                        if sess.account:
                            self._auth_sessions[sess.account] = sess
                for sel_dict in data.get("sellers", []):
                    sel = DarazSeller(**sel_dict)
                    self._sellers[sel.seller_id] = sel
                for cat_dict in data.get("categories", []):
                    cat = DarazCategory(**cat_dict)
                    self._categories[cat.category_id] = cat
                for q_dict in data.get("quotas", []):
                    q = DarazDailyQuota(**q_dict)
                    self._quotas[q.date] = q
                for t_dict in data.get("training_dataset", []):
                    tr = DarazTrainingDataset(**t_dict)
                    self._training_dataset[tr.id] = tr
        except Exception:
            pass

    def _save_to_disk(self):
        if not self._storage_file or self._storage_file == ":memory:":
            return
        if os.getenv("TESTING") == "true":
            return
        if self.is_testing_environment() and self._storage_file == self._prod_storage_file:
            return
        try:
            unique_sessions = {
                s.id: s for s in self._auth_sessions.values()
                if not self.is_test_session(s)
            }
            payload = {
                "products": [p.model_dump(mode="json") for p in self._products.values()],
                "snapshots": [s.model_dump(mode="json") for s in self._snapshots[-2000:]],
                "auth_sessions": [s.model_dump(mode="json") for s in unique_sessions.values()],
                "sellers": [s.model_dump(mode="json") for s in self._sellers.values()],
                "categories": [c.model_dump(mode="json") for c in self._categories.values()],
                "quotas": [q.model_dump(mode="json") for q in self._quotas.values()],
                "training_dataset": [t.model_dump(mode="json") for t in self._training_dataset.values()]
            }
            temp_file = self._storage_file + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            if os.path.exists(self._storage_file):
                os.replace(temp_file, self._storage_file)
            else:
                os.rename(temp_file, self._storage_file)
        except Exception:
            pass

    def upsert_product(self, product: MarketplaceProduct) -> MarketplaceProduct:
        with self._lock:
            key = self._get_key(product.platform, product.product_id)
            now = datetime.now(timezone.utc)
            if key in self._products:
                existing = self._products[key]
                # Preserve first_seen_at and original created_at
                updated = product.model_copy(update={
                    "first_seen_at": existing.first_seen_at,
                    "created_at": existing.created_at,
                    "last_seen_at": product.last_seen_at or now,
                    "last_synced_at": product.last_synced_at or now,
                    "updated_at": now
                })
                self._products[key] = updated
                self._save_to_disk()
                return updated.model_copy()
            else:
                new_prod = product.model_copy(update={
                    "first_seen_at": product.first_seen_at or now,
                    "last_seen_at": product.last_seen_at or now,
                    "last_synced_at": product.last_synced_at or now,
                    "created_at": product.created_at or now,
                    "updated_at": product.updated_at or now
                })
                self._products[key] = new_prod
                self._save_to_disk()
                return new_prod.model_copy()

    save_product = upsert_product

    def batch_upsert_products(self, products: List[MarketplaceProduct]) -> List[MarketplaceProduct]:
        with self._lock:
            now = datetime.now(timezone.utc)
            results = []
            for product in products:
                key = self._get_key(product.platform, product.product_id)
                if key in self._products:
                    existing = self._products[key]
                    updated = product.model_copy(update={
                        "first_seen_at": existing.first_seen_at,
                        "created_at": existing.created_at,
                        "last_seen_at": product.last_seen_at or now,
                        "last_synced_at": product.last_synced_at or now,
                        "updated_at": now
                    })
                    self._products[key] = updated
                    results.append(updated.model_copy())
                else:
                    new_prod = product.model_copy(update={
                        "first_seen_at": product.first_seen_at or now,
                        "last_seen_at": product.last_seen_at or now,
                        "last_synced_at": product.last_synced_at or now,
                        "created_at": product.created_at or now,
                        "updated_at": now
                    })
                    self._products[key] = new_prod
                    results.append(new_prod.model_copy())
            self._save_to_disk()
            return results

    def get_product(self, platform: str, product_id: str) -> Optional[MarketplaceProduct]:
        with self._lock:
            key = self._get_key(platform, product_id)
            prod = self._products.get(key)
            return prod.model_copy() if prod else None

    def list_products(
        self,
        platform: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[MarketplaceProduct]:
        with self._lock:
            prods = list(self._products.values())
            if platform and platform != "all":
                plat_lower = platform.lower()
                prods = [p for p in prods if p.platform.lower() == plat_lower]
            if category and category != "all":
                cat_lower = category.lower()
                prods = [
                    p for p in prods
                    if (p.category and cat_lower in p.category.lower())
                    or (cat_lower in p.product_name.lower())
                ]
            if search and search.strip():
                s_lower = search.strip().lower()
                prods = [
                    p for p in prods
                    if s_lower in p.product_name.lower()
                    or (p.seller_name and s_lower in p.seller_name.lower())
                    or (p.category and s_lower in p.category.lower())
                ]

            # Sort by last_synced_at descending, then rating descending
            prods.sort(key=lambda p: (p.last_synced_at, p.rating, p.review_count), reverse=True)
            return [p.model_copy() for p in prods[offset:offset + limit]]

    def count_products(self, platform: Optional[str] = None, category: Optional[str] = None) -> int:
        with self._lock:
            prods = list(self._products.values())
            if platform and platform != "all":
                plat_lower = platform.lower()
                prods = [p for p in prods if p.platform.lower() == plat_lower]
            if category and category != "all":
                cat_lower = category.lower()
                prods = [p for p in prods if p.category and cat_lower in p.category.lower()]
            return len(prods)

    def create_snapshot(self, snapshot: ProductMarketSnapshot) -> ProductMarketSnapshot:
        with self._lock:
            self._snapshots.append(snapshot.model_copy())
            self._save_to_disk()
            return snapshot.model_copy()

    def batch_create_snapshots(self, snapshots: List[ProductMarketSnapshot]) -> List[ProductMarketSnapshot]:
        with self._lock:
            for s in snapshots:
                self._snapshots.append(s.model_copy())
            self._save_to_disk()
            return [s.model_copy() for s in snapshots]

    def get_snapshots(self, platform: str, product_id: str, limit: int = 50) -> List[ProductMarketSnapshot]:
        with self._lock:
            p_id = str(product_id).strip()
            plat = platform.lower()
            snaps = [
                s.model_copy() for s in self._snapshots
                if s.platform.lower() == plat and s.product_id == p_id
            ]
            snaps.sort(key=lambda s: s.observed_at, reverse=True)
            return snaps[:limit]

    def get_latest_sync_metadata(self, platform: str = "daraz") -> Dict[str, Any]:
        with self._lock:
            plat_lower = platform.lower()
            prods = [p for p in self._products.values() if p.platform.lower() == plat_lower]
            if not prods:
                return {
                    "is_live": False,
                    "data_source": "none",
                    "last_synced_at": None,
                    "data_age_seconds": None,
                    "total_records": 0
                }
            latest_sync = max(p.last_synced_at for p in prods)
            now = datetime.now(timezone.utc)
            age_seconds = int((now - latest_sync).total_seconds()) if latest_sync else None
            return {
                "is_live": age_seconds is not None and age_seconds < 300,
                "data_source": "daraz_live" if (age_seconds is not None and age_seconds < 300) else "database_cache",
                "last_synced_at": latest_sync.isoformat() if latest_sync else None,
                "data_age_seconds": max(0, age_seconds) if age_seconds is not None else None,
                "total_records": len(prods)
            }

    def save_auth_session(self, session: DarazAuthSession) -> DarazAuthSession:
        with self._lock:
            key = session.seller_id or session.account or session.id
            self._auth_sessions[key] = session.model_copy()
            # Also index by session.id
            self._auth_sessions[session.id] = session.model_copy()
            if not self.is_testing_environment() and not self.is_test_session(session):
                self._save_to_disk()
            return session.model_copy()

    def get_auth_session(self, seller_id_or_account: Optional[str] = None) -> Optional[DarazAuthSession]:
        with self._lock:
            if seller_id_or_account:
                sess = self._auth_sessions.get(seller_id_or_account)
                return sess.model_copy() if sess else None
            # Return latest active session
            if not self._auth_sessions:
                return None
            sessions = list(self._auth_sessions.values())
            sessions.sort(key=lambda s: s.updated_at, reverse=True)
            return sessions[0].model_copy()

    def list_auth_sessions(self) -> List[DarazAuthSession]:
        with self._lock:
            # Deduplicate by id
            seen = set()
            res = []
            for s in self._auth_sessions.values():
                if s.id not in seen:
                    seen.add(s.id)
                    res.append(s.model_copy())
            res.sort(key=lambda s: s.updated_at, reverse=True)
            return res

    def get_provider_health(self, provider_name: str) -> Optional[DarazProviderHealth]:
        with self._lock:
            h = self._provider_health.get(provider_name)
            return h.model_copy() if h else None

    def update_provider_health(self, health: DarazProviderHealth) -> DarazProviderHealth:
        with self._lock:
            self._provider_health[health.provider_name] = health.model_copy()
            return health.model_copy()

    def list_provider_health(self) -> List[DarazProviderHealth]:
        with self._lock:
            healths = list(self._provider_health.values())
            healths.sort(key=lambda h: h.priority)
            return [h.model_copy() for h in healths]

    def upsert_seller(self, seller: DarazSeller) -> DarazSeller:
        with self._lock:
            now = datetime.now(timezone.utc)
            clean_id = str(seller.seller_id).strip()
            if clean_id in self._sellers:
                existing = self._sellers[clean_id]
                updated = seller.model_copy(update={
                    "created_at": existing.created_at,
                    "updated_at": now
                })
                self._sellers[clean_id] = updated
                return updated.model_copy()
            else:
                self._sellers[clean_id] = seller.model_copy()
                return seller.model_copy()

    def get_seller(self, seller_id: str) -> Optional[DarazSeller]:
        with self._lock:
            s = self._sellers.get(str(seller_id).strip())
            return s.model_copy() if s else None

    def list_sellers(self, limit: int = 50, offset: int = 0) -> List[DarazSeller]:
        with self._lock:
            sellers = list(self._sellers.values())
            sellers.sort(key=lambda s: s.updated_at, reverse=True)
            return [s.model_copy() for s in sellers[offset:offset + limit]]

    def upsert_category(self, category: DarazCategory) -> DarazCategory:
        with self._lock:
            now = datetime.now(timezone.utc)
            clean_id = str(category.category_id).strip()
            if clean_id in self._categories:
                existing = self._categories[clean_id]
                updated = category.model_copy(update={
                    "created_at": existing.created_at,
                    "updated_at": now
                })
                self._categories[clean_id] = updated
                return updated.model_copy()
            else:
                self._categories[clean_id] = category.model_copy()
                return category.model_copy()

    def get_category(self, category_id: str) -> Optional[DarazCategory]:
        with self._lock:
            c = self._categories.get(str(category_id).strip())
            return c.model_copy() if c else None

    def list_categories(self, parent_id: Optional[str] = None) -> List[DarazCategory]:
        with self._lock:
            cats = list(self._categories.values())
            if parent_id is not None:
                cats = [c for c in cats if c.parent_id == str(parent_id).strip()]
            cats.sort(key=lambda c: (c.level, c.name))
            return [c.model_copy() for c in cats]

    def create_review(self, review: DarazReview) -> DarazReview:
        with self._lock:
            self._reviews[review.review_id] = review.model_copy()
            return review.model_copy()

    def list_reviews(self, product_id: str, limit: int = 50) -> List[DarazReview]:
        with self._lock:
            clean_id = str(product_id).strip()
            reviews = [r.model_copy() for r in self._reviews.values() if r.product_id == clean_id]
            reviews.sort(key=lambda r: (r.review_date or r.created_at), reverse=True)
            return reviews[:limit]

    def create_ingestion_run(self, run: DarazIngestionRun) -> DarazIngestionRun:
        with self._lock:
            self._ingestion_runs[run.id] = run.model_copy()
            return run.model_copy()

    def update_ingestion_run(self, run: DarazIngestionRun) -> DarazIngestionRun:
        with self._lock:
            self._ingestion_runs[run.id] = run.model_copy()
            return run.model_copy()

    def get_ingestion_run(self, run_id: str) -> Optional[DarazIngestionRun]:
        with self._lock:
            r = self._ingestion_runs.get(run_id)
            return r.model_copy() if r else None

    def list_ingestion_runs(self, limit: int = 50) -> List[DarazIngestionRun]:
        with self._lock:
            runs = list(self._ingestion_runs.values())
            runs.sort(key=lambda r: r.started_at, reverse=True)
            return [r.model_copy() for r in runs[:limit]]

    def record_api_telemetry(self, telemetry: DarazApiTelemetry) -> DarazApiTelemetry:
        with self._lock:
            self._telemetry.append(telemetry.model_copy())
            if len(self._telemetry) > 5000:
                self._telemetry = self._telemetry[-5000:]
            return telemetry.model_copy()

    def get_api_telemetry(self, limit: int = 100) -> List[DarazApiTelemetry]:
        with self._lock:
            telemetry_copy = [t.model_copy() for t in self._telemetry]
            telemetry_copy.sort(key=lambda t: t.created_at, reverse=True)
            return telemetry_copy[:limit]

    def get_or_create_daily_quota(self, date: Optional[str] = None, daily_limit: int = 6000000) -> DarazDailyQuota:
        with self._lock:
            today_str = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if today_str not in self._quotas:
                now = datetime.now(timezone.utc)
                self._quotas[today_str] = DarazDailyQuota(
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
            return self._quotas[today_str].model_copy()

    def increment_daily_quota(self, date: Optional[str] = None, count: int = 1, is_rate_limited: bool = False) -> DarazDailyQuota:
        with self._lock:
            today_str = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            now = datetime.now(timezone.utc)
            if today_str not in self._quotas:
                self._quotas[today_str] = DarazDailyQuota(
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
            else:
                q = self._quotas[today_str]
                q.requests_used += count
                q.remaining = max(0, q.daily_limit - q.requests_used)
                if is_rate_limited:
                    q.rate_limit_hits += 1
                q.last_request_at = now
                q.updated_at = now
            return self._quotas[today_str].model_copy()

    def add_training_dataset_item(self, item: DarazTrainingDataset) -> DarazTrainingDataset:
        with self._lock:
            self._training_dataset[item.id] = item.model_copy()
            return item.model_copy()

    def list_training_dataset(self, category: Optional[str] = None, limit: int = 100) -> List[DarazTrainingDataset]:
        with self._lock:
            items = list(self._training_dataset.values())
            if category and category != "all":
                c_lower = category.lower()
                items = [i for i in items if c_lower in i.category.lower()]
            items.sort(key=lambda i: (i.quality_score, i.created_at), reverse=True)
            return [i.model_copy() for i in items[:limit]]

class InMemoryShopifyRepository(ShopifyRepository):
    def __init__(self, store_path: Optional[str] = None):
        self._lock = threading.Lock()
        self._products: Dict[str, ShopifyProduct] = {}  # key: f"{store_domain}:{product_id}"
        self._snapshots: List[ShopifyProductSnapshot] = []
        self._health: Dict[str, ShopifyProviderHealth] = {}
        self._sync_runs: List[ShopifySyncRun] = []
        self._store_path = store_path or os.path.join(os.path.dirname(__file__), "..", "data", "shopify_store.json")
        self._init_default_providers()
        self._load_from_disk()

    def _init_default_providers(self):
        defaults = [
            ("shopify_scout", 1),
            ("shopscraper", 2),
            ("shopify_apps_spy", 3),
            ("xtracto", 4),
            ("bornoo", 5),
        ]
        now = datetime.now(timezone.utc)
        for name, priority in defaults:
            self._health[name] = ShopifyProviderHealth(
                id=f"prov_{name}",
                provider_name=name,
                priority=priority,
                enabled=True,
                status="healthy",
                consecutive_failures=0,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                rate_limited_requests=0,
                created_at=now,
                updated_at=now
            )

    def _load_from_disk(self):
        try:
            if os.path.exists(self._store_path):
                with open(self._store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("products", []):
                        prod = ShopifyProduct.model_validate(item)
                        key = f"{prod.store_domain.lower()}:{str(prod.product_id).strip()}"
                        self._products[key] = prod
                    for snap in data.get("snapshots", []):
                        self._snapshots.append(ShopifyProductSnapshot.model_validate(snap))
                    for h_item in data.get("health", []):
                        h = ShopifyProviderHealth.model_validate(h_item)
                        self._health[h.provider_name] = h
                    for r_item in data.get("sync_runs", []):
                        self._sync_runs.append(ShopifySyncRun.model_validate(r_item))
        except Exception:
            pass

    def _save_to_disk(self):
        try:
            os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
            data = {
                "products": [p.model_dump(mode="json") for p in self._products.values()],
                "snapshots": [s.model_dump(mode="json") for s in self._snapshots[-2000:]],
                "health": [h.model_dump(mode="json") for h in self._health.values()],
                "sync_runs": [r.model_dump(mode="json") for r in self._sync_runs[-200:]]
            }
            with open(self._store_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    def upsert_product(self, product: ShopifyProduct) -> ShopifyProduct:
        with self._lock:
            key = f"{product.store_domain.lower()}:{str(product.product_id).strip()}"
            now = datetime.now(timezone.utc)
            if key in self._products:
                existing = self._products[key]
                updated = product.model_copy(update={
                    "id": existing.id,
                    "first_seen_at": existing.first_seen_at,
                    "last_seen_at": now,
                    "last_synced_at": now,
                    "updated_at": now,
                })
                self._products[key] = updated
                self._save_to_disk()
                return updated.model_copy()
            else:
                new_prod = product.model_copy(update={
                    "first_seen_at": product.first_seen_at or now,
                    "last_seen_at": now,
                    "last_synced_at": now,
                    "created_at": product.created_at or now,
                    "updated_at": now
                })
                self._products[key] = new_prod
                self._save_to_disk()
                return new_prod.model_copy()

    def batch_upsert_products(self, products: List[ShopifyProduct]) -> List[ShopifyProduct]:
        with self._lock:
            results = []
            now = datetime.now(timezone.utc)
            for product in products:
                key = f"{product.store_domain.lower()}:{str(product.product_id).strip()}"
                if key in self._products:
                    existing = self._products[key]
                    updated = product.model_copy(update={
                        "id": existing.id,
                        "first_seen_at": existing.first_seen_at,
                        "last_seen_at": now,
                        "last_synced_at": now,
                        "updated_at": now,
                    })
                    self._products[key] = updated
                    results.append(updated.model_copy())
                else:
                    new_prod = product.model_copy(update={
                        "first_seen_at": product.first_seen_at or now,
                        "last_seen_at": now,
                        "last_synced_at": now,
                        "created_at": product.created_at or now,
                        "updated_at": now
                    })
                    self._products[key] = new_prod
                    results.append(new_prod.model_copy())
            self._save_to_disk()
            return results

    def get_product(self, store_domain: str, product_id: str) -> Optional[ShopifyProduct]:
        with self._lock:
            key = f"{store_domain.lower()}:{str(product_id).strip()}"
            prod = self._products.get(key)
            return prod.model_copy() if prod else None

    def get_product_by_id(self, id: str) -> Optional[ShopifyProduct]:
        with self._lock:
            for p in self._products.values():
                if p.id == id or p.product_id == id:
                    return p.model_copy()
            return None

    def list_products(
        self,
        store_domain: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ShopifyProduct]:
        with self._lock:
            prods = list(self._products.values())
            if store_domain and store_domain != "all":
                dom_lower = store_domain.lower()
                prods = [p for p in prods if dom_lower in p.store_domain.lower()]
            if category and category != "all":
                cat_lower = category.lower()
                prods = [p for p in prods if (p.category and cat_lower in p.category.lower()) or (p.product_type and cat_lower in p.product_type.lower())]
            if search and search.strip():
                s_lower = search.strip().lower()
                prods = [
                    p for p in prods
                    if s_lower in p.title.lower()
                    or (p.vendor and s_lower in p.vendor.lower())
                    or (p.category and s_lower in p.category.lower())
                    or any(s_lower in tag.lower() for tag in p.tags)
                ]

            if sort_by == "price_asc":
                prods.sort(key=lambda p: p.price)
            elif sort_by == "price_desc":
                prods.sort(key=lambda p: p.price, reverse=True)
            elif sort_by == "rating":
                prods.sort(key=lambda p: (p.rating, p.review_count), reverse=True)
            else:
                prods.sort(key=lambda p: (p.last_synced_at, p.rating), reverse=True)

            return [p.model_copy() for p in prods[offset:offset + limit]]

    def count_products(
        self,
        store_domain: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> int:
        with self._lock:
            prods = list(self._products.values())
            if store_domain and store_domain != "all":
                dom_lower = store_domain.lower()
                prods = [p for p in prods if dom_lower in p.store_domain.lower()]
            if category and category != "all":
                cat_lower = category.lower()
                prods = [p for p in prods if (p.category and cat_lower in p.category.lower()) or (p.product_type and cat_lower in p.product_type.lower())]
            if search and search.strip():
                s_lower = search.strip().lower()
                prods = [
                    p for p in prods
                    if s_lower in p.title.lower()
                    or (p.vendor and s_lower in p.vendor.lower())
                    or (p.category and s_lower in p.category.lower())
                    or any(s_lower in tag.lower() for tag in p.tags)
                ]
            return len(prods)

    def create_snapshot(self, snapshot: ShopifyProductSnapshot) -> ShopifyProductSnapshot:
        with self._lock:
            self._snapshots.append(snapshot.model_copy())
            self._save_to_disk()
            return snapshot.model_copy()

    def batch_create_snapshots(self, snapshots: List[ShopifyProductSnapshot]) -> List[ShopifyProductSnapshot]:
        with self._lock:
            for s in snapshots:
                self._snapshots.append(s.model_copy())
            self._save_to_disk()
            return [s.model_copy() for s in snapshots]

    def get_snapshots(self, store_domain: str, product_id: str, limit: int = 50) -> List[ShopifyProductSnapshot]:
        with self._lock:
            p_id = str(product_id).strip()
            dom = store_domain.lower()
            snaps = [
                s.model_copy() for s in self._snapshots
                if s.store_domain.lower() == dom and s.product_id == p_id
            ]
            snaps.sort(key=lambda s: s.observed_at, reverse=True)
            return snaps[:limit]

    def get_provider_health(self, provider_name: str) -> Optional[ShopifyProviderHealth]:
        with self._lock:
            h = self._health.get(provider_name)
            return h.model_copy() if h else None

    def list_provider_health(self) -> List[ShopifyProviderHealth]:
        with self._lock:
            items = list(self._health.values())
            items.sort(key=lambda h: h.priority)
            return [h.model_copy() for h in items]

    def update_provider_health(self, health: ShopifyProviderHealth) -> ShopifyProviderHealth:
        with self._lock:
            h_copy = health.model_copy(update={"updated_at": datetime.now(timezone.utc)})
            self._health[health.provider_name] = h_copy
            self._save_to_disk()
            return h_copy.model_copy()

    def record_sync_run(self, sync_run: ShopifySyncRun) -> ShopifySyncRun:
        with self._lock:
            self._sync_runs.append(sync_run.model_copy())
            self._save_to_disk()
            return sync_run.model_copy()

    def list_sync_runs(self, store_domain: Optional[str] = None, limit: int = 20) -> List[ShopifySyncRun]:
        with self._lock:
            runs = self._sync_runs
            if store_domain and store_domain != "all":
                dom_lower = store_domain.lower()
                runs = [r for r in runs if dom_lower in r.store_domain.lower()]
            runs_sorted = sorted(runs, key=lambda r: r.started_at, reverse=True)
            return [r.model_copy() for r in runs_sorted[:limit]]

    def get_latest_sync_metadata(self, store_domain: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            prods = list(self._products.values())
            if store_domain and store_domain != "all":
                dom_lower = store_domain.lower()
                prods = [p for p in prods if dom_lower in p.store_domain.lower()]
            if not prods:
                return {
                    "is_live": False,
                    "data_source": "none",
                    "last_synced_at": None,
                    "data_age_seconds": None,
                    "total_records": 0
                }
            latest_sync = max(p.last_synced_at for p in prods)
            now = datetime.now(timezone.utc)
            age_seconds = int((now - latest_sync).total_seconds()) if latest_sync else None
            return {
                "is_live": age_seconds is not None and age_seconds < 300,
                "data_source": "shopify_live" if (age_seconds is not None and age_seconds < 300) else "database_cache",
                "last_synced_at": latest_sync.isoformat() if latest_sync else None,
                "data_age_seconds": max(0, age_seconds) if age_seconds is not None else None,
                "total_records": len(prods)
            }


class InMemoryUnifiedProductRepository(UnifiedProductRepository):
    def __init__(self, data_file: Optional[str] = ":default:"):
        self._lock = threading.Lock()
        if data_file == ":default:":
            self._data_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "data", "unified_products_store.json"
            )
        else:
            self._data_file = data_file
        self._unified_products: Dict[str, UnifiedProduct] = {}
        self._platform_listings: Dict[str, ProductPlatformListing] = {}
        self._match_candidates: List[ProductMatchCandidate] = []
        self._match_audits: Dict[str, ProductMatchAudit] = {}
        self._match_decisions: Dict[str, ProductMatchDecision] = {}
        self._product_match_decisions: Dict[str, List[ProductMatchDecision]] = {}

        if self._data_file:
            self._load_from_disk()

    def clear(self) -> None:
        with self._lock:
            self._unified_products.clear()
            self._platform_listings.clear()
            self._match_candidates.clear()
            self._match_audits.clear()
            self._match_decisions.clear()
            self._product_match_decisions.clear()

    def _get_listing_key(self, platform: str, platform_product_id: str, store_domain: Optional[str] = None) -> str:
        dom = (store_domain or "").strip().lower()
        return f"{platform.strip().lower()}:{platform_product_id.strip().lower()}:{dom}"

    def _load_from_disk(self) -> None:
        if os.path.exists(self._data_file):
            try:
                with open(self._data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("unified_products", []):
                        p = UnifiedProduct(**item)
                        self._unified_products[p.unified_product_id] = p
                    for item in data.get("platform_listings", []):
                        l = ProductPlatformListing(**item)
                        key = self._get_listing_key(l.platform, l.platform_product_id, l.store_domain)
                        self._platform_listings[key] = l
                    for item in data.get("match_candidates", []):
                        self._match_candidates.append(ProductMatchCandidate(**item))
                    for item in data.get("match_audits", []):
                        a = ProductMatchAudit(**item)
                        self._match_audits[a.unified_product_id] = a
                    for item in data.get("match_decisions", []):
                        d = ProductMatchDecision(**item)
                        self._match_decisions[d.id] = d
                        for pid in [d.product_a_id, d.product_b_id, d.unified_product_id]:
                            if pid:
                                if pid not in self._product_match_decisions:
                                    self._product_match_decisions[pid] = []
                                self._product_match_decisions[pid].append(d)
            except Exception as e:
                pass

    def _save_to_disk(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._data_file), exist_ok=True)
            temp_file = f"{self._data_file}.tmp"
            data = {
                "unified_products": [p.model_dump(mode="json") for p in self._unified_products.values()],
                "platform_listings": [l.model_dump(mode="json") for l in self._platform_listings.values()],
                "match_candidates": [c.model_dump(mode="json") for c in self._match_candidates],
                "match_audits": [a.model_dump(mode="json") for a in self._match_audits.values()],
                "match_decisions": [d.model_dump(mode="json") for d in self._match_decisions.values()]
            }
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            if os.path.exists(self._data_file):
                os.remove(self._data_file)
            os.rename(temp_file, self._data_file)
        except Exception:
            pass


    def upsert_unified_product(self, product: UnifiedProduct) -> UnifiedProduct:
        with self._lock:
            existing = self._unified_products.get(product.unified_product_id)
            if existing:
                # Preserve first_seen_at
                product.first_seen_at = existing.first_seen_at
                product.created_at = existing.created_at
                product.updated_at = datetime.now(timezone.utc)
            self._unified_products[product.unified_product_id] = product
            self._save_to_disk()
            return product

    def get_unified_product(self, unified_product_id: str) -> Optional[UnifiedProduct]:
        with self._lock:
            return self._unified_products.get(unified_product_id)

    def find_by_normalized_name(self, normalized_name: str) -> List[UnifiedProduct]:
        with self._lock:
            norm = normalized_name.strip().lower()
            return [p for p in self._unified_products.values() if p.normalized_name.lower() == norm]

    def find_by_brand(self, brand: str) -> List[UnifiedProduct]:
        with self._lock:
            b_lower = brand.strip().lower()
            return [p for p in self._unified_products.values() if p.brand and p.brand.lower() == b_lower]

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
        with self._lock:
            results = list(self._unified_products.values())

            if category and category.lower() != "all":
                c_lower = category.lower()
                results = [p for p in results if p.category and c_lower in p.category.lower()]

            if brand and brand.lower() != "all":
                b_lower = brand.lower()
                results = [p for p in results if p.brand and b_lower == p.brand.lower()]

            if platform and platform.lower() != "all":
                p_lower = platform.lower()
                matching_prod_ids = {
                    l.unified_product_id for l in self._platform_listings.values()
                    if l.platform.lower() == p_lower
                }
                results = [p for p in results if p.unified_product_id in matching_prod_ids]

            if search and search.strip():
                q = search.strip().lower()
                results = [
                    p for p in results
                    if q in p.canonical_name.lower()
                    or q in p.normalized_name.lower()
                    or (p.brand and q in p.brand.lower())
                    or (p.category and q in p.category.lower())
                    or any(q in str(v).lower() for v in p.identifiers.values())
                ]

            # Price / Availability / Rating filters based on listings
            if min_price is not None or max_price is not None or available is not None or min_rating is not None:
                filtered = []
                for p in results:
                    listings = [l for l in self._platform_listings.values() if l.unified_product_id == p.unified_product_id]
                    if not listings:
                        continue
                    if min_price is not None and not any(l.price >= min_price for l in listings):
                        continue
                    if max_price is not None and not any(l.price <= max_price for l in listings):
                        continue
                    if available is not None and not any(l.available == available for l in listings):
                        continue
                    if min_rating is not None and not any(l.rating >= min_rating for l in listings):
                        continue
                    filtered.append(p)
                results = filtered

            # Sorting
            if sort_by == "name_asc":
                results.sort(key=lambda x: x.canonical_name.lower())
            elif sort_by == "name_desc":
                results.sort(key=lambda x: x.canonical_name.lower(), reverse=True)
            elif sort_by == "oldest":
                results.sort(key=lambda x: x.first_seen_at)
            else:
                # Default: recently updated
                results.sort(key=lambda x: x.last_seen_at, reverse=True)

            return results[offset : offset + limit]

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
        return len(self.list_unified_products(
            category=category,
            brand=brand,
            platform=platform,
            search=search,
            min_price=min_price,
            max_price=max_price,
            available=available,
            min_rating=min_rating,
            limit=100000,
            offset=0
        ))

    def upsert_platform_listing(self, listing: ProductPlatformListing) -> ProductPlatformListing:
        with self._lock:
            key = self._get_listing_key(listing.platform, listing.platform_product_id, listing.store_domain)
            existing = self._platform_listings.get(key)
            if existing:
                listing.created_at = existing.created_at
                listing.updated_at = datetime.now(timezone.utc)
            self._platform_listings[key] = listing
            self._save_to_disk()
            return listing

    def get_platform_listing(self, platform: str, platform_product_id: str, store_domain: Optional[str] = None) -> Optional[ProductPlatformListing]:
        with self._lock:
            key = self._get_listing_key(platform, platform_product_id, store_domain)
            return self._platform_listings.get(key)

    def list_listings_for_product(self, unified_product_id: str) -> List[ProductPlatformListing]:
        with self._lock:
            return [l for l in self._platform_listings.values() if l.unified_product_id == unified_product_id]

    def list_all_listings(self) -> List[ProductPlatformListing]:
        with self._lock:
            return list(self._platform_listings.values())

    def record_match_audit(self, audit: ProductMatchAudit) -> ProductMatchAudit:
        with self._lock:
            self._match_audits[audit.unified_product_id] = audit
            self._save_to_disk()
            return audit

    def get_match_audit(self, unified_product_id: str) -> Optional[ProductMatchAudit]:
        with self._lock:
            return self._match_audits.get(unified_product_id)

    def list_match_audits(self, unified_product_id: Optional[str] = None, limit: int = 50) -> List[ProductMatchAudit]:
        with self._lock:
            if unified_product_id:
                aud = self._match_audits.get(unified_product_id)
                return [aud] if aud else []
            return list(self._match_audits.values())[:limit]

    def record_match_candidate(self, candidate: ProductMatchCandidate) -> ProductMatchCandidate:
        with self._lock:
            # Check if exists
            for i, c in enumerate(self._match_candidates):
                if c.id == candidate.id:
                    self._match_candidates[i] = candidate
                    self._save_to_disk()
                    return candidate
            self._match_candidates.append(candidate)
            self._save_to_disk()
            return candidate

    def get_match_candidate(self, candidate_id: str) -> Optional[ProductMatchCandidate]:
        with self._lock:
            for c in self._match_candidates:
                if c.id == candidate_id:
                    return c.model_copy()
            return None

    def update_match_candidate(self, candidate: ProductMatchCandidate) -> ProductMatchCandidate:
        with self._lock:
            for i, c in enumerate(self._match_candidates):
                if c.id == candidate.id:
                    self._match_candidates[i] = candidate
                    self._save_to_disk()
                    return candidate
            self._match_candidates.append(candidate)
            self._save_to_disk()
            return candidate

    def list_match_candidates(
        self,
        unified_product_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ProductMatchCandidate]:
        with self._lock:
            res = list(self._match_candidates)
            if unified_product_id:
                res = [c for c in res if c.unified_product_id == unified_product_id or c.candidate_unified_id == unified_product_id]
            if status:
                res = [c for c in res if c.status.lower() == status.lower()]
            res.sort(key=lambda x: x.created_at, reverse=True)
            return [c.model_copy() for c in res[offset : offset + limit]]

    def record_match_decision(self, decision: ProductMatchDecision) -> ProductMatchDecision:
        with self._lock:
            self._match_decisions[decision.id] = decision.model_copy()
            for pid in [decision.product_a_id, decision.product_b_id, decision.unified_product_id]:
                if pid:
                    if pid not in self._product_match_decisions:
                        self._product_match_decisions[pid] = []
                    self._product_match_decisions[pid].append(decision.model_copy())
            self._save_to_disk()
            return decision.model_copy()

    def get_match_decision(self, decision_id: str) -> Optional[ProductMatchDecision]:
        with self._lock:
            d = self._match_decisions.get(decision_id)
            return d.model_copy() if d else None

    def list_match_decisions(
        self,
        product_id: Optional[str] = None,
        unified_product_id: Optional[str] = None,
        limit: int = 50
    ) -> List[ProductMatchDecision]:
        with self._lock:
            if product_id and product_id in self._product_match_decisions:
                return [d.model_copy() for d in self._product_match_decisions[product_id][-limit:]]
            if unified_product_id and unified_product_id in self._product_match_decisions:
                return [d.model_copy() for d in self._product_match_decisions[unified_product_id][-limit:]]
            all_decs = sorted(list(self._match_decisions.values()), key=lambda x: x.created_at, reverse=True)
            return [d.model_copy() for d in all_decs[:limit]]



class InMemoryLLMUsageRepository(LLMUsageRepository):
    def __init__(self, data_file: Optional[str] = ":default:"):
        self._lock = threading.Lock()
        self._records: List[LLMUsageRecord] = []
        if data_file == ":default:":
            self._data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "llm_usage_store.json")
        else:
            self._data_file = data_file
        if self._data_file:
            self._load_from_disk()

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


    def _load_from_disk(self) -> None:
        if not os.path.exists(self._data_file):
            return
        try:
            with open(self._data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("records", []):
                    item["created_at"] = datetime.fromisoformat(item["created_at"])
                    self._records.append(LLMUsageRecord(**item))
        except Exception:
            pass

    def _save_to_disk(self) -> None:
        if not self._data_file:
            return
        try:
            os.makedirs(os.path.dirname(self._data_file), exist_ok=True)
            payload = {
                "records": [r.model_dump(mode="json") for r in self._records]
            }
            tmp_file = f"{self._data_file}.tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp_file, self._data_file)
        except Exception:
            pass

    def record_usage(self, record: LLMUsageRecord) -> LLMUsageRecord:
        with self._lock:
            self._records.append(record)
            self._save_to_disk()
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
        with self._lock:
            res = list(self._records)
            if user_id:
                res = [r for r in res if r.user_id == user_id]
            if workspace_id:
                res = [r for r in res if r.workspace_id == workspace_id]
            if provider:
                res = [r for r in res if r.provider.lower() == provider.lower()]
            if request_type:
                res = [r for r in res if r.request_type.lower() == request_type.lower()]
            res.sort(key=lambda x: x.created_at, reverse=True)
            return res[offset : offset + limit]

    def get_summary(self, user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            records = self._records
            if user_id:
                records = [r for r in records if r.user_id == user_id]
            if workspace_id:
                records = [r for r in records if r.workspace_id == workspace_id]

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


class InMemoryDataQualityRepository(DataQualityRepository):
    """
    Thread-safe in-memory repository for AI Agent registry, execution runs,
    persistent memory, memory mutation events, and data quality validation results.
    """

    def __init__(self, data_file: Optional[str] = ":default:"):
        self._lock = threading.Lock()
        if data_file == ":default:":
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
            os.makedirs(data_dir, exist_ok=True)
            self._data_file = os.path.join(data_dir, "in_memory_data_quality.json")
        else:
            self._data_file = data_file

        self._agents: Dict[str, AIAgent] = {}
        self._runs: List[AIAgentRun] = []
        self._memories: Dict[str, AIAgentMemory] = {}
        self._memory_events: List[AIAgentMemoryEvent] = []
        self._validation_results: List[DataQualityValidationResult] = []

        # Preseed Agent 1: Data Quality & Validation Agent
        default_agent = AIAgent(
            id="agent_data_quality",
            name="Data Quality & Validation Agent",
            slug="data-quality",
            agent_type="data_quality",
            status="active",
            description="Continuous marketplace data validation, anomaly detection, deterministic scoring (0-100), and selective Gemini LLM ambiguity resolution.",
            version="1.0.0",
            capabilities=[
                "missing_field_detection",
                "impossible_value_sanity",
                "freshness_enforcement",
                "duplicate_detection",
                "deterministic_scoring",
                "gemini_ambiguity_resolution",
                "provider_memory_learning"
            ],
            configuration={
                "strict_mode": True,
                "gemini_enabled": True,
                "rejection_threshold": 50.0,
                "warning_threshold": 70.0,
                "staleness_days": 30
            },
            metadata_json={"author": "TrendPulse AI Team", "tier": "production"}
        )
        self._agents[default_agent.id] = default_agent

        self._load_from_disk()

    def _load_from_disk(self):
        if not self._data_file or self._data_file == ":memory:" or not os.path.exists(self._data_file):
            return
        try:
            with open(self._data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for a_dict in data.get("agents", []):
                    a = AIAgent(**a_dict)
                    self._agents[a.id] = a
                for r_dict in data.get("runs", []):
                    r = AIAgentRun(**r_dict)
                    self._runs.append(r)
                for m_dict in data.get("memories", []):
                    m = AIAgentMemory(**m_dict)
                    key = f"{m.agent_id}:{m.memory_type}:{m.memory_key}"
                    self._memories[key] = m
                for e_dict in data.get("memory_events", []):
                    e = AIAgentMemoryEvent(**e_dict)
                    self._memory_events.append(e)
                for v_dict in data.get("validation_results", []):
                    v = DataQualityValidationResult(**v_dict)
                    self._validation_results.append(v)
        except Exception:
            pass

    def _save_to_disk(self):
        if not self._data_file or self._data_file == ":memory:":
            return
        try:
            payload = {
                "agents": [a.model_dump(mode="json") for a in self._agents.values()],
                "runs": [r.model_dump(mode="json") for r in self._runs[-200:]],
                "memories": [m.model_dump(mode="json") for m in self._memories.values()],
                "memory_events": [e.model_dump(mode="json") for e in self._memory_events[-500:]],
                "validation_results": [v.model_dump(mode="json") for v in self._validation_results[-1000:]]
            }
            temp_file = self._data_file + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            if os.path.exists(self._data_file):
                os.replace(temp_file, self._data_file)
            else:
                os.rename(temp_file, self._data_file)
        except Exception:
            pass

    def get_agent(self, agent_id: str) -> Optional[AIAgent]:
        with self._lock:
            agent = self._agents.get(agent_id)
            return agent.model_copy() if agent else None

    def upsert_agent(self, agent: AIAgent) -> AIAgent:
        with self._lock:
            now = datetime.now(timezone.utc)
            updated = agent.model_copy(update={"updated_at": now})
            self._agents[agent.id] = updated
            self._save_to_disk()
            return updated.model_copy()

    def create_agent_run(self, run: AIAgentRun) -> AIAgentRun:
        with self._lock:
            self._runs.append(run.model_copy())
            self._save_to_disk()
            return run.model_copy()

    def update_agent_run(self, run: AIAgentRun) -> AIAgentRun:
        with self._lock:
            for idx, existing in enumerate(self._runs):
                if existing.id == run.id:
                    self._runs[idx] = run.model_copy()
                    self._save_to_disk()
                    return run.model_copy()
            self._runs.append(run.model_copy())
            self._save_to_disk()
            return run.model_copy()

    def get_agent_run(self, run_id: str) -> Optional[AIAgentRun]:
        with self._lock:
            for r in self._runs:
                if r.id == run_id:
                    return r.model_copy()
            return None

    def list_agent_runs(self, agent_id: str, workspace_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[AIAgentRun]:
        with self._lock:
            res = [r for r in self._runs if r.agent_id == agent_id]
            if workspace_id:
                res = [r for r in res if r.workspace_id in [workspace_id, None]]
            res.sort(key=lambda x: x.started_at, reverse=True)
            return [r.model_copy() for r in res[offset : offset + limit]]

    def get_memory(self, agent_id: str, memory_type: str, memory_key: str) -> Optional[AIAgentMemory]:
        with self._lock:
            key = f"{agent_id}:{memory_type}:{memory_key}"
            mem = self._memories.get(key)
            return mem.model_copy() if mem else None

    def upsert_memory(self, memory: AIAgentMemory) -> AIAgentMemory:
        with self._lock:
            key = f"{memory.agent_id}:{memory.memory_type}:{memory.memory_key}"
            now = datetime.now(timezone.utc)
            if key in self._memories:
                existing = self._memories[key]
                updated = memory.model_copy(update={
                    "id": existing.id,
                    "created_at": existing.created_at,
                    "updated_at": now,
                    "last_observed_at": now
                })
                self._memories[key] = updated
            else:
                new_mem = memory.model_copy(update={"created_at": now, "updated_at": now, "last_observed_at": now})
                self._memories[key] = new_mem
            self._save_to_disk()
            return self._memories[key].model_copy()

    def list_memories(self, agent_id: str, memory_type: Optional[str] = None) -> List[AIAgentMemory]:
        with self._lock:
            res = [m for m in self._memories.values() if m.agent_id == agent_id]
            if memory_type:
                res = [m for m in res if m.memory_type == memory_type]
            res.sort(key=lambda x: x.last_observed_at, reverse=True)
            return [m.model_copy() for m in res]

    def record_memory_event(self, event: AIAgentMemoryEvent) -> AIAgentMemoryEvent:
        with self._lock:
            self._memory_events.append(event.model_copy())
            self._save_to_disk()
            return event.model_copy()

    def list_memory_events(self, agent_id: str, memory_id: Optional[str] = None, limit: int = 50) -> List[AIAgentMemoryEvent]:
        with self._lock:
            res = [e for e in self._memory_events if e.agent_id == agent_id]
            if memory_id:
                res = [e for e in res if e.memory_id == memory_id]
            res.sort(key=lambda x: x.created_at, reverse=True)
            return [e.model_copy() for e in res[:limit]]

    def save_validation_result(self, result: DataQualityValidationResult) -> DataQualityValidationResult:
        with self._lock:
            self._validation_results.append(result.model_copy())
            self._save_to_disk()
            return result.model_copy()

    def get_validation_result(self, result_id: str) -> Optional[DataQualityValidationResult]:
        with self._lock:
            for v in self._validation_results:
                if v.id == result_id:
                    return v.model_copy()
            return None

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
        with self._lock:
            res = self._validation_results
            if workspace_id:
                res = [v for v in res if v.workspace_id in [workspace_id, None]]
            if platform:
                res = [v for v in res if v.platform.lower() == platform.lower()]
            if classification:
                res = [v for v in res if v.classification.lower() == classification.lower()]
            if source_provider:
                res = [v for v in res if v.source_provider.lower() == source_provider.lower()]
            if min_score is not None:
                res = [v for v in res if v.overall_score >= min_score]
            if max_score is not None:
                res = [v for v in res if v.overall_score <= max_score]
            res.sort(key=lambda x: x.validated_at, reverse=True)
            return [v.model_copy() for v in res[offset : offset + limit]]

    def count_validation_results(
        self,
        workspace_id: Optional[str] = None,
        platform: Optional[str] = None,
        classification: Optional[str] = None,
        source_provider: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None
    ) -> int:
        with self._lock:
            res = self._validation_results
            if workspace_id:
                res = [v for v in res if v.workspace_id in [workspace_id, None]]
            if platform:
                res = [v for v in res if v.platform.lower() == platform.lower()]
            if classification:
                res = [v for v in res if v.classification.lower() == classification.lower()]
            if source_provider:
                res = [v for v in res if v.source_provider.lower() == source_provider.lower()]
            if min_score is not None:
                res = [v for v in res if v.overall_score >= min_score]
            if max_score is not None:
                res = [v for v in res if v.overall_score <= max_score]
            return len(res)

    def get_quality_summary(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            res = self._validation_results
            if workspace_id:
                res = [v for v in res if v.workspace_id in [workspace_id, None]]

            total = len(res)
            valid = len([v for v in res if v.classification == "valid"])
            warning = len([v for v in res if v.classification == "valid_with_warnings"])
            review = len([v for v in res if v.classification == "needs_review"])
            rejected = len([v for v in res if v.classification == "rejected"])
            avg_score = round(sum(v.overall_score for v in res) / max(1, total), 1) if total else 100.0

            # Provider breakdown
            providers = list(set(v.source_provider for v in res))
            provider_stats = []
            for p in providers:
                p_items = [v for v in res if v.source_provider == p]
                p_total = len(p_items)
                p_val = len([v for v in p_items if v.classification == "valid"])
                p_warn = len([v for v in p_items if v.classification == "valid_with_warnings"])
                p_rej = len([v for v in p_items if v.classification == "rejected"])
                p_score = round(sum(v.overall_score for v in p_items) / max(1, p_total), 1)
                
                # collect top issues
                issue_counts = {}
                for v in p_items:
                    for iss in v.issues + v.warnings:
                        issue_counts[iss.rule_name] = issue_counts.get(iss.rule_name, 0) + 1
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
                "total_memory_items": len(self._memories),
                "provider_reliabilities": provider_stats,
                "total_runs": len(self._runs),
                "last_run_at": self._runs[-1].started_at if self._runs else None
            }

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
        with self._lock:
            res = list(self._validation_results)
            if platform and platform != "all":
                res = [v for v in res if v.platform.lower() == platform.lower()]
            if provider and provider != "all":
                res = [v for v in res if (v.source_provider or "").lower() == provider.lower()]
            if classification and classification != "all":
                res = [v for v in res if v.classification.lower() == classification.lower()]
            if normalized_category and normalized_category != "all":
                cat_lower = normalized_category.lower()
                res = [v for v in res if (v.normalized_category and cat_lower in v.normalized_category.lower()) or (v.original_category and cat_lower in v.original_category.lower())]
            if rejection_reason and rejection_reason != "all":
                reason_lower = rejection_reason.lower()
                def _has_reason(v):
                    for r in v.rejection_reasons or []:
                        if reason_lower in str(r).lower():
                            return True
                    for iss in v.issues or []:
                        msg = iss.message if hasattr(iss, "message") else (iss.get("message", "") if isinstance(iss, dict) else str(iss))
                        rule = iss.rule_name if hasattr(iss, "rule_name") else (iss.get("rule_name", "") if isinstance(iss, dict) else "")
                        if reason_lower in msg.lower() or reason_lower in rule.lower():
                            return True
                    return False
                res = [v for v in res if _has_reason(v)]
            if search and search.strip():
                s_lower = search.strip().lower()
                def _matches_search(v):
                    if s_lower in (v.product_name or "").lower():
                        return True
                    if s_lower in (v.product_title or "").lower():
                        return True
                    if s_lower in (v.platform_product_id or "").lower():
                        return True
                    if s_lower in (v.normalized_category or "").lower():
                        return True
                    if s_lower in (v.original_category or "").lower():
                        return True
                    return False
                res = [v for v in res if _matches_search(v)]
            if min_score is not None:
                res = [v for v in res if (v.quality_score or v.overall_score) >= min_score]
            if max_score is not None:
                res = [v for v in res if (v.quality_score or v.overall_score) <= max_score]
            if date_from is not None:
                res = [v for v in res if v.validated_at >= date_from]
            if date_to is not None:
                res = [v for v in res if v.validated_at <= date_to]

            # Sorting
            if sort_by == "score_asc":
                res_sorted = sorted(res, key=lambda x: (x.quality_score or x.overall_score))
            elif sort_by == "score_desc":
                res_sorted = sorted(res, key=lambda x: (x.quality_score or x.overall_score), reverse=True)
            elif sort_by == "price_asc":
                res_sorted = sorted(res, key=lambda x: (x.price or 0.0))
            elif sort_by == "price_desc":
                res_sorted = sorted(res, key=lambda x: (x.price or 0.0), reverse=True)
            elif sort_by == "validated_at_asc":
                res_sorted = sorted(res, key=lambda x: x.validated_at)
            else:
                # Default: validated_at_desc
                res_sorted = sorted(res, key=lambda x: x.validated_at, reverse=True)

            total = len(res_sorted)
            paginated = res_sorted[offset : offset + limit]
            items = [self._to_public_item(v) for v in paginated]
            return items, total


    def get_public_stats(self) -> PublicDataQualityStatsResponse:
        with self._lock:
            res = self._validation_results
            total = len(res)
            rejected = len([v for v in res if v.classification.lower() == "rejected"])
            warnings = len([v for v in res if v.classification.lower() == "valid_with_warnings"])
            valid = len([v for v in res if v.classification.lower() == "valid"])
            avg_score = round(sum(v.overall_score for v in res) / max(1, total), 1) if total else 100.0
            
            # Top rejection reasons
            reason_counts: Dict[str, int] = {}
            for v in res:
                if v.classification.lower() == "rejected":
                    for r in v.rejection_reasons or []:
                        reason_counts[r] = reason_counts.get(r, 0) + 1
                    if not v.rejection_reasons:
                        for iss in v.issues:
                            msg = iss.message if hasattr(iss, "message") else str(iss)
                            reason_counts[msg] = reason_counts.get(msg, 0) + 1
            top_reasons = [{"reason": k, "count": v} for k, v in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:10]]

            # Platform breakdown
            plat_counts: Dict[str, Dict[str, Any]] = {}
            for v in res:
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

            # Category breakdown
            cat_counts: Dict[str, Dict[str, Any]] = {}
            for v in res:
                cat = v.normalized_category or "Unknown"
                if cat not in cat_counts:
                    cat_counts[cat] = {"category": cat, "total": 0, "rejected": 0}
                cat_counts[cat]["total"] += 1
                if v.classification.lower() == "rejected":
                    cat_counts[cat]["rejected"] += 1
            cat_breakdown = sorted(list(cat_counts.values()), key=lambda x: x["total"], reverse=True)[:10]

            latest_time = max([v.validated_at for v in res], default=datetime.now(timezone.utc))

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
        with self._lock:
            plat_lower = platform.lower()
            p_id = str(platform_product_id).strip()
            matches = [
                v for v in self._validation_results
                if v.platform.lower() == plat_lower and str(v.platform_product_id).strip() == p_id
            ]
            matches.sort(key=lambda x: x.validated_at, reverse=True)
            return [v.model_copy() for v in matches[offset : offset + limit]]

    def clear(self):

        with self._lock:
            self._runs.clear()
            self._memories.clear()
            self._memory_events.clear()
            self._validation_results.clear()
            if self._data_file and self._data_file != ":memory:" and os.path.exists(self._data_file):
                try:
                    os.remove(self._data_file)
                except Exception:
                    pass


class InMemoryTaxonomyRepository(TaxonomyRepository):
    def __init__(self, data_file: Optional[str] = None):
        self._lock = threading.RLock()

        self._categories: Dict[str, TaxonomyCategory] = {}
        self._assignments: Dict[str, ProductTaxonomyAssignment] = {}
        self._unified_assignments: Dict[str, List[ProductTaxonomyAssignment]] = {}
        self._candidates: List[ProductTaxonomyCandidate] = []
        self._memories: Dict[str, AIAgentMemory] = {}
        self._memory_events: List[AIAgentMemoryEvent] = []
        self._init_default_categories()

    def _init_default_categories(self):
        now = datetime.now(timezone.utc)
        for cat_node in CENTRAL_TAXONOMY_TREE:
            cat_name = cat_node["name"]
            cat_slug = cat_node["slug"]
            cat_id = f"cat_{cat_slug.replace('-', '_')}"
            top_cat = TaxonomyCategory(
                id=cat_id,
                parent_id=None,
                name=cat_name,
                slug=cat_slug,
                level=1,
                description=cat_node.get("description", ""),
                is_active=True,
                created_at=now,
                updated_at=now
            )
            self._categories[cat_id] = top_cat

            for sub_node in cat_node.get("subcategories", []):
                sub_name = sub_node["name"]
                sub_slug = sub_node["slug"]
                sub_id = f"sub_{sub_slug.replace('-', '_')}"
                sub_cat = TaxonomyCategory(
                    id=sub_id,
                    parent_id=cat_id,
                    name=sub_name,
                    slug=sub_slug,
                    level=2,
                    description=f"{sub_name} in {cat_name}",
                    is_active=True,
                    created_at=now,
                    updated_at=now
                )
                self._categories[sub_id] = sub_cat

                for pt_node in sub_node.get("product_types", []):
                    pt_name = pt_node["name"]
                    pt_slug = pt_node["slug"]
                    pt_id = f"pt_{pt_slug.replace('-', '_')}"
                    pt_cat = TaxonomyCategory(
                        id=pt_id,
                        parent_id=sub_id,
                        name=pt_name,
                        slug=pt_slug,
                        level=4,
                        description=f"{pt_name} product type",
                        is_active=True,
                        metadata_json={"keywords": pt_node.get("keywords", [])},
                        created_at=now,
                        updated_at=now
                    )
                    self._categories[pt_id] = pt_cat

    def get_category_by_id(self, category_id: str) -> Optional[TaxonomyCategory]:
        with self._lock:
            cat = self._categories.get(category_id)
            return cat.model_copy() if cat else None

    def get_category_by_slug(self, slug: str) -> Optional[TaxonomyCategory]:
        with self._lock:
            s_lower = slug.strip().lower()
            for cat in self._categories.values():
                if cat.slug.lower() == s_lower:
                    return cat.model_copy()
            return None

    def list_categories(self, parent_id: Optional[str] = None, level: Optional[int] = None) -> List[TaxonomyCategory]:
        with self._lock:
            res = list(self._categories.values())
            if parent_id is not None:
                if parent_id == "null" or parent_id == "":
                    res = [c for c in res if c.parent_id is None]
                else:
                    res = [c for c in res if c.parent_id == parent_id]
            if level is not None:
                res = [c for c in res if c.level == level]
            res.sort(key=lambda x: (x.level, x.name))
            return [c.model_copy() for c in res]

    def get_taxonomy_tree(self) -> List[TaxonomyCategory]:
        with self._lock:
            # Build recursive tree from memory
            counts = self.get_category_product_counts()
            top_level = [c.model_copy() for c in self._categories.values() if c.parent_id is None]
            top_level.sort(key=lambda x: x.name)

            for top in top_level:
                top.product_count = counts.get(top.name, 0)
                subs = [c.model_copy() for c in self._categories.values() if c.parent_id == top.id]
                subs.sort(key=lambda x: x.name)
                for sub in subs:
                    sub.product_count = counts.get(f"{top.name}>{sub.name}", 0)
                    pts = [c.model_copy() for c in self._categories.values() if c.parent_id == sub.id]
                    pts.sort(key=lambda x: x.name)
                    for pt in pts:
                        pt.product_count = counts.get(f"{top.name}>{sub.name}>{pt.name}", 0)
                    sub.children = pts
                top.children = subs

            return top_level

    def search_categories(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            q = query.strip().lower()
            results = []
            counts = self.get_category_product_counts()
            for cat in self._categories.values():
                if q in cat.name.lower() or q in cat.slug.lower() or (cat.description and q in cat.description.lower()):
                    # Build path
                    path = [cat.name]
                    curr_p = cat.parent_id
                    while curr_p and curr_p in self._categories:
                        p_obj = self._categories[curr_p]
                        path.insert(0, p_obj.name)
                        curr_p = p_obj.parent_id

                    results.append({
                        "id": cat.id,
                        "name": cat.name,
                        "slug": cat.slug,
                        "level": cat.level,
                        "path": path,
                        "product_count": counts.get(cat.name, 0)
                    })
                    if len(results) >= limit:
                        break
            return results

    def create_category(self, category: TaxonomyCategory) -> TaxonomyCategory:
        with self._lock:
            self._categories[category.id] = category.model_copy()
            return category.model_copy()

    def update_category(self, category: TaxonomyCategory) -> TaxonomyCategory:
        with self._lock:
            self._categories[category.id] = category.model_copy()
            return category.model_copy()

    def get_assignment_by_unified_product_id(self, unified_product_id: str) -> Optional[ProductTaxonomyAssignment]:
        with self._lock:
            u_id = unified_product_id.strip()
            history = self._unified_assignments.get(u_id, [])
            if history:
                return history[-1].model_copy()
            for a in self._assignments.values():
                if a.unified_product_id == u_id:
                    return a.model_copy()
            return None

    def get_assignment_history(self, unified_product_id: str, limit: int = 50) -> List[ProductTaxonomyAssignment]:
        with self._lock:
            u_id = unified_product_id.strip()
            history = self._unified_assignments.get(u_id, [])
            history_sorted = sorted(history, key=lambda x: x.created_at, reverse=True)
            return [a.model_copy() for a in history_sorted[:limit]]

    def upsert_assignment(self, assignment: ProductTaxonomyAssignment) -> ProductTaxonomyAssignment:
        with self._lock:
            self._assignments[assignment.id] = assignment.model_copy()
            u_id = assignment.unified_product_id.strip()
            if u_id not in self._unified_assignments:
                self._unified_assignments[u_id] = []
            self._unified_assignments[u_id].append(assignment.model_copy())
            return assignment.model_copy()

    def create_candidate(self, candidate: ProductTaxonomyCandidate) -> ProductTaxonomyCandidate:
        with self._lock:
            self._candidates.append(candidate.model_copy())
            return candidate.model_copy()

    def list_candidates(self, limit: int = 50, offset: int = 0) -> List[ProductTaxonomyCandidate]:
        with self._lock:
            sorted_cands = sorted(self._candidates, key=lambda x: x.created_at, reverse=True)
            return [c.model_copy() for c in sorted_cands[offset : offset + limit]]

    def get_category_product_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        with self._lock:
            for a in self._assignments.values():
                cat = a.category
                sub = a.subcategory
                pt = a.product_type
                if cat:
                    counts[cat] = counts.get(cat, 0) + 1
                if cat and sub and sub != "Unknown":
                    key_sub = f"{cat}>{sub}"
                    counts[key_sub] = counts.get(key_sub, 0) + 1
                if cat and sub and pt and pt != "Unknown":
                    key_pt = f"{cat}>{sub}>{pt}"
                    counts[key_pt] = counts.get(key_pt, 0) + 1
        return counts

    def get_memory(self, agent_id: str, memory_type: str, memory_key: str) -> Optional[AIAgentMemory]:
        with self._lock:
            composite_key = f"{agent_id}:{memory_type}:{memory_key.strip().lower()}"
            mem = self._memories.get(composite_key)
            return mem.model_copy() if mem else None

    def upsert_memory(self, memory: AIAgentMemory) -> AIAgentMemory:
        with self._lock:
            composite_key = f"{memory.agent_id}:{memory.memory_type}:{memory.memory_key.strip().lower()}"
            self._memories[composite_key] = memory.model_copy()
            return memory.model_copy()

    def list_memory(self, agent_id: str, memory_type: Optional[str] = None) -> List[AIAgentMemory]:
        with self._lock:
            res = [m for m in self._memories.values() if m.agent_id == agent_id]
            if memory_type:
                res = [m for m in res if m.memory_type == memory_type]
            res.sort(key=lambda x: x.updated_at, reverse=True)
            return [m.model_copy() for m in res]

    def record_memory_event(self, event: AIAgentMemoryEvent) -> AIAgentMemoryEvent:
        with self._lock:
            self._memory_events.append(event.model_copy())
            return event.model_copy()

    def get_memory_events(self, agent_id: str, memory_id: Optional[str] = None, limit: int = 50) -> List[AIAgentMemoryEvent]:
        with self._lock:
            res = [e for e in self._memory_events if e.agent_id == agent_id]
            if memory_id:
                res = [e for e in res if e.memory_id == memory_id]
            res.sort(key=lambda x: x.created_at, reverse=True)
            return [e.model_copy() for e in res[:limit]]

    def clear(self):
        with self._lock:
            self._categories.clear()
            self._assignments.clear()
            self._unified_assignments.clear()
            self._candidates.clear()
            self._memories.clear()
            self._memory_events.clear()
            self._init_default_categories()



class InMemoryTrendDetectionRepository(TrendDetectionRepository):
    def __init__(self):
        self._lock = threading.RLock()
        self._observations: Dict[str, TrendObservation] = {}
        self._product_observations: Dict[str, List[TrendObservation]] = {}
        self._signals: Dict[str, TrendSignal] = {}
        self._product_signals: Dict[str, List[TrendSignal]] = {}
        self._fingerprints: Dict[str, str] = {}  # fingerprint -> signal_id
        self._candidates: Dict[str, TrendSignalCandidate] = {}
        self._audits: List[TrendDetectionAudit] = []

    def record_observation(self, observation: TrendObservation) -> TrendObservation:
        with self._lock:
            self._observations[observation.id] = observation.model_copy()
            u_id = observation.unified_product_id.strip()
            if u_id not in self._product_observations:
                self._product_observations[u_id] = []
            self._product_observations[u_id].append(observation.model_copy())
            return observation.model_copy()

    def batch_record_observations(self, observations: List[TrendObservation]) -> List[TrendObservation]:
        with self._lock:
            res = []
            for obs in observations:
                res.append(self.record_observation(obs))
            return res

    def list_observations(
        self,
        unified_product_id: str,
        metric_type: Optional[str] = None,
        platform: Optional[str] = None,
        start_time: Optional[datetime] = None,
        limit: int = 50
    ) -> List[TrendObservation]:
        with self._lock:
            u_id = unified_product_id.strip()
            obs_list = self._product_observations.get(u_id, [])
            filtered = obs_list
            if metric_type:
                filtered = [o for o in filtered if o.metric_type == metric_type]
            if platform:
                filtered = [o for o in filtered if o.platform.lower() == platform.lower()]
            if start_time:
                filtered = [o for o in filtered if o.observed_at >= start_time]
            sorted_obs = sorted(filtered, key=lambda x: x.observed_at, reverse=True)
            return [o.model_copy() for o in sorted_obs[:limit]]

    def upsert_signal(self, signal: TrendSignal) -> TrendSignal:
        with self._lock:
            self._signals[signal.id] = signal.model_copy()
            if signal.fingerprint:
                self._fingerprints[signal.fingerprint] = signal.id
            u_id = signal.unified_product_id.strip()
            if u_id not in self._product_signals:
                self._product_signals[u_id] = []
            # Replace if already exists in product_signals
            self._product_signals[u_id] = [
                s for s in self._product_signals[u_id] if s.id != signal.id
            ]
            self._product_signals[u_id].append(signal.model_copy())
            return signal.model_copy()

    def get_signal_by_fingerprint(self, fingerprint: str) -> Optional[TrendSignal]:
        with self._lock:
            sig_id = self._fingerprints.get(fingerprint)
            if sig_id and sig_id in self._signals:
                return self._signals[sig_id].model_copy()
            return None

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
    ) -> List[TrendSignal]:
        with self._lock:
            if unified_product_id:
                signals = self._product_signals.get(unified_product_id.strip(), [])
            else:
                signals = list(self._signals.values())

            filtered = signals
            if signal_type:
                filtered = [s for s in filtered if s.signal_type == signal_type]
            if direction:
                filtered = [s for s in filtered if s.direction == direction]
            if severity:
                filtered = [s for s in filtered if s.severity == severity]
            if status:
                filtered = [s for s in filtered if s.status == status]
            if min_strength is not None:
                filtered = [s for s in filtered if s.signal_strength >= min_strength]

            sorted_signals = sorted(filtered, key=lambda x: x.detected_at, reverse=True)
            return [s.model_copy() for s in sorted_signals[offset : offset + limit]]

    def count_signals(
        self,
        unified_product_id: Optional[str] = None,
        signal_type: Optional[str] = None,
        direction: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        with self._lock:
            if unified_product_id:
                signals = self._product_signals.get(unified_product_id.strip(), [])
            else:
                signals = list(self._signals.values())

            filtered = signals
            if signal_type:
                filtered = [s for s in filtered if s.signal_type == signal_type]
            if direction:
                filtered = [s for s in filtered if s.direction == direction]
            if severity:
                filtered = [s for s in filtered if s.severity == severity]
            if status:
                filtered = [s for s in filtered if s.status == status]
            return len(filtered)

    def create_candidate(self, candidate: TrendSignalCandidate) -> TrendSignalCandidate:
        with self._lock:
            self._candidates[candidate.id] = candidate.model_copy()
            return candidate.model_copy()

    def get_candidate(self, candidate_id: str) -> Optional[TrendSignalCandidate]:
        with self._lock:
            cand = self._candidates.get(candidate_id)
            return cand.model_copy() if cand else None

    def list_candidates(
        self,
        status: Optional[str] = None,
        candidate_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TrendSignalCandidate]:
        with self._lock:
            filtered = list(self._candidates.values())
            if status:
                filtered = [c for c in filtered if c.status == status]
            if candidate_type:
                filtered = [c for c in filtered if c.candidate_type == candidate_type]
            sorted_cands = sorted(filtered, key=lambda x: x.created_at, reverse=True)
            return [c.model_copy() for c in sorted_cands[offset : offset + limit]]

    def resolve_candidate(
        self,
        candidate_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[TrendSignalCandidate]:
        with self._lock:
            cand = self._candidates.get(candidate_id)
            if not cand:
                return None
            updated = cand.model_copy(update={
                "status": status,
                "metadata": {**cand.metadata, "resolution_notes": notes or "", "resolved_at": datetime.now(timezone.utc).isoformat()},
                "updated_at": datetime.now(timezone.utc)
            })
            self._candidates[candidate_id] = updated
            return updated.model_copy()

    def record_audit(self, audit: TrendDetectionAudit) -> TrendDetectionAudit:
        with self._lock:
            self._audits.append(audit.model_copy())
            return audit.model_copy()

    def list_audits(
        self,
        product_id: Optional[str] = None,
        agent_id: str = "agent_trend_detection",
        limit: int = 50
    ) -> List[TrendDetectionAudit]:
        with self._lock:
            res = [a for a in self._audits if a.agent_id == agent_id]
            if product_id:
                res = [a for a in res if a.product_id == product_id]
            sorted_audits = sorted(res, key=lambda x: x.created_at, reverse=True)
            return [a.model_copy() for a in sorted_audits[:limit]]

    def get_trend_stats(self) -> AgentTrendDetectionStats:
        with self._lock:
            total_prods = len(self._product_signals)
            all_signals = list(self._signals.values())
            active_signals = [s for s in all_signals if s.status == "active"]
            candidates = list(self._candidates.values())
            breakouts = [c for c in candidates if c.candidate_type == "breakout_candidate" and c.status == "pending_review"]
            gemini_calls = len([a for a in self._audits if a.llm_used])

            by_type: Dict[str, int] = {}
            by_dir: Dict[str, int] = {}
            by_sev: Dict[str, int] = {}
            platform_breakdown: Dict[str, int] = {}

            for s in active_signals:
                by_type[s.signal_type] = by_type.get(s.signal_type, 0) + 1
                by_dir[s.direction] = by_dir.get(s.direction, 0) + 1
                by_sev[s.severity] = by_sev.get(s.severity, 0) + 1
                for p in s.platforms:
                    platform_breakdown[p] = platform_breakdown.get(p, 0) + 1

            return AgentTrendDetectionStats(
                total_analyzed_products=total_prods,
                total_signals_detected=len(all_signals),
                active_signals_count=len(active_signals),
                breakout_candidates_count=len(breakouts),
                gemini_invocations_count=gemini_calls,
                signals_by_type=by_type,
                signals_by_direction=by_dir,
                signals_by_severity=by_sev,
                platform_breakdown=platform_breakdown,
                last_updated=datetime.now(timezone.utc)
            )

    def clear(self):
        with self._lock:
            self._observations.clear()
            self._product_observations.clear()
            self._signals.clear()
            self._product_signals.clear()
            self._fingerprints.clear()
            self._candidates.clear()
            self._audits.clear()


class InMemoryAnomalyDetectionRepository(AnomalyDetectionRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._observations: Dict[str, AnomalyObservation] = {}
        self._product_observations: Dict[str, List[str]] = {}  # unified_product_id -> [obs_id]
        self._anomalies: Dict[str, AnomalyDetection] = {}
        self._product_anomalies: Dict[str, List[str]] = {}  # unified_product_id -> [anomaly_id]
        self._fingerprints: Dict[str, str] = {}  # fingerprint -> anomaly_id
        self._candidates: Dict[str, AnomalyCandidate] = {}
        self._audits: List[AnomalyDetectionAudit] = []

    def record_observation(self, observation: AnomalyObservation) -> AnomalyObservation:
        with self._lock:
            self._observations[observation.id] = observation
            if observation.unified_product_id not in self._product_observations:
                self._product_observations[observation.unified_product_id] = []
            if observation.id not in self._product_observations[observation.unified_product_id]:
                self._product_observations[observation.unified_product_id].append(observation.id)
            return observation

    def batch_record_observations(self, observations: List[AnomalyObservation]) -> List[AnomalyObservation]:
        with self._lock:
            for obs in observations:
                self._observations[obs.id] = obs
                if obs.unified_product_id not in self._product_observations:
                    self._product_observations[obs.unified_product_id] = []
                if obs.id not in self._product_observations[obs.unified_product_id]:
                    self._product_observations[obs.unified_product_id].append(obs.id)
            return observations

    def list_observations(
        self,
        unified_product_id: str,
        metric_type: Optional[str] = None,
        platform: Optional[str] = None,
        start_time: Optional[datetime] = None,
        limit: int = 50
    ) -> List[AnomalyObservation]:
        with self._lock:
            obs_ids = self._product_observations.get(unified_product_id, [])
            results = []
            for oid in obs_ids:
                obs = self._observations.get(oid)
                if not obs:
                    continue
                if metric_type and obs.metric_type.lower() != metric_type.lower():
                    continue
                if platform and obs.platform.lower() != platform.lower():
                    continue
                if start_time and obs.observed_at < start_time:
                    continue
                results.append(obs)
            # Sort newest first
            results.sort(key=lambda x: x.observed_at, reverse=True)
            return results[:limit]

    def upsert_anomaly(self, anomaly: AnomalyDetection) -> AnomalyDetection:
        with self._lock:
            if anomaly.fingerprint and anomaly.fingerprint in self._fingerprints:
                existing_id = self._fingerprints[anomaly.fingerprint]
                existing = self._anomalies.get(existing_id)
                if existing:
                    updated = existing.model_copy(update={
                        "score": anomaly.score,
                        "confidence": anomaly.confidence,
                        "observed_value": anomaly.observed_value,
                        "deviation": anomaly.deviation,
                        "deviation_percent": anomaly.deviation_percent,
                        "evidence": anomaly.evidence,
                        "status": anomaly.status,
                        "updated_at": datetime.now(timezone.utc)
                    })
                    self._anomalies[existing_id] = updated
                    return updated

            self._anomalies[anomaly.id] = anomaly
            if anomaly.fingerprint:
                self._fingerprints[anomaly.fingerprint] = anomaly.id
            if anomaly.unified_product_id not in self._product_anomalies:
                self._product_anomalies[anomaly.unified_product_id] = []
            if anomaly.id not in self._product_anomalies[anomaly.unified_product_id]:
                self._product_anomalies[anomaly.unified_product_id].append(anomaly.id)
            return anomaly

    def get_anomaly_by_fingerprint(self, fingerprint: str) -> Optional[AnomalyDetection]:
        with self._lock:
            aid = self._fingerprints.get(fingerprint)
            return self._anomalies.get(aid) if aid else None

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
    ) -> List[AnomalyDetection]:
        with self._lock:
            if unified_product_id:
                a_ids = self._product_anomalies.get(unified_product_id, [])
                candidates = [self._anomalies[aid] for aid in a_ids if aid in self._anomalies]
            else:
                candidates = list(self._anomalies.values())

            filtered = []
            for a in candidates:
                if anomaly_type and anomaly_type != "all" and a.anomaly_type.lower() != anomaly_type.lower():
                    continue
                if severity and severity != "all" and a.severity.lower() != severity.lower():
                    continue
                if status and status != "all" and a.status.lower() != status.lower():
                    continue
                if platform and platform != "all" and platform.lower() not in [p.lower() for p in a.platforms]:
                    continue
                if min_score is not None and a.score < min_score:
                    continue
                filtered.append(a)

            filtered.sort(key=lambda x: x.detected_at, reverse=True)
            return filtered[offset: offset + limit]

    def count_anomalies(
        self,
        unified_product_id: Optional[str] = None,
        anomaly_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        platform: Optional[str] = None
    ) -> int:
        with self._lock:
            if unified_product_id:
                a_ids = self._product_anomalies.get(unified_product_id, [])
                candidates = [self._anomalies[aid] for aid in a_ids if aid in self._anomalies]
            else:
                candidates = list(self._anomalies.values())

            count = 0
            for a in candidates:
                if anomaly_type and anomaly_type != "all" and a.anomaly_type.lower() != anomaly_type.lower():
                    continue
                if severity and severity != "all" and a.severity.lower() != severity.lower():
                    continue
                if status and status != "all" and a.status.lower() != status.lower():
                    continue
                if platform and platform != "all" and platform.lower() not in [p.lower() for p in a.platforms]:
                    continue
                count += 1
            return count

    def create_candidate(self, candidate: AnomalyCandidate) -> AnomalyCandidate:
        with self._lock:
            self._candidates[candidate.id] = candidate
            return candidate

    def get_candidate(self, candidate_id: str) -> Optional[AnomalyCandidate]:
        with self._lock:
            return self._candidates.get(candidate_id)

    def list_candidates(
        self,
        status: Optional[str] = None,
        candidate_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AnomalyCandidate]:
        with self._lock:
            items = list(self._candidates.values())
            filtered = []
            for c in items:
                if status and status != "all" and c.status.lower() != status.lower():
                    continue
                if candidate_type and candidate_type != "all" and c.candidate_type.lower() != candidate_type.lower():
                    continue
                filtered.append(c)
            filtered.sort(key=lambda x: x.created_at, reverse=True)
            return filtered[offset: offset + limit]

    def resolve_candidate(
        self,
        candidate_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[AnomalyCandidate]:
        with self._lock:
            cand = self._candidates.get(candidate_id)
            if not cand:
                return None
            meta = dict(cand.metadata)
            if notes:
                meta["resolution_notes"] = notes
            updated = cand.model_copy(update={
                "status": status,
                "metadata": meta,
                "updated_at": datetime.now(timezone.utc)
            })
            self._candidates[candidate_id] = updated
            return updated

    def record_audit(self, audit: AnomalyDetectionAudit) -> AnomalyDetectionAudit:
        with self._lock:
            self._audits.append(audit)
            return audit

    def list_audits(
        self,
        product_id: Optional[str] = None,
        agent_id: str = "agent_anomaly_detection",
        limit: int = 50
    ) -> List[AnomalyDetectionAudit]:
        with self._lock:
            res = [
                a for a in self._audits
                if a.agent_id == agent_id and (product_id is None or a.product_id == product_id)
            ]
            res.sort(key=lambda x: x.created_at, reverse=True)
            return res[:limit]

    def get_anomaly_stats(self) -> AgentAnomalyDetectionStats:
        with self._lock:
            all_anomalies = list(self._anomalies.values())
            active_anomalies = [a for a in all_anomalies if a.status == "active"]
            criticals = [a for a in all_anomalies if a.severity == "critical"]
            highs = [a for a in all_anomalies if a.severity == "high"]
            pending_cands = [c for c in self._candidates.values() if c.status == "pending_review"]
            false_positives = [a for a in all_anomalies if a.status == "false_positive"]

            by_type: Dict[str, int] = {}
            by_sev: Dict[str, int] = {}
            by_plat: Dict[str, int] = {}

            for a in all_anomalies:
                by_type[a.anomaly_type] = by_type.get(a.anomaly_type, 0) + 1
                by_sev[a.severity] = by_sev.get(a.severity, 0) + 1
                for p in a.platforms:
                    by_plat[p] = by_plat.get(p, 0) + 1

            return AgentAnomalyDetectionStats(
                total_analyzed_products=len(self._product_observations),
                total_anomalies_detected=len(all_anomalies),
                active_anomalies_count=len(active_anomalies),
                critical_anomalies_count=len(criticals),
                high_severity_count=len(highs),
                candidates_pending_review=len(pending_cands),
                false_positives_count=len(false_positives),
                anomalies_by_type=by_type,
                anomalies_by_severity=by_sev,
                anomalies_by_platform=by_plat,
                last_updated=datetime.now(timezone.utc)
            )

    def clear(self):
        with self._lock:
            self._observations.clear()
            self._product_observations.clear()
            self._anomalies.clear()
            self._product_anomalies.clear()
            self._fingerprints.clear()
            self._candidates.clear()
            self._audits.clear()



class InMemoryRecommendationRepository(RecommendationRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._recommendations: Dict[str, ProductRecommendation] = {}
        self._product_recommendations: Dict[str, List[str]] = {} # unified_product_id -> list of rec_ids
        self._fingerprints: Dict[str, str] = {} # fingerprint -> rec_id
        self._candidates: Dict[str, RecommendationCandidate] = {}
        self._interactions: List[RecommendationInteraction] = []
        self._audits: List[RecommendationAudit] = []
        self._memories: Dict[str, AIAgentMemory] = {}
        self._memory_events: List[AIAgentMemoryEvent] = []

    def save_recommendation(self, recommendation: ProductRecommendation) -> ProductRecommendation:
        with self._lock:
            # Check fingerprint
            if recommendation.fingerprint and recommendation.fingerprint in self._fingerprints:
                existing_id = self._fingerprints[recommendation.fingerprint]
                if existing_id in self._recommendations:
                    # Update existing
                    self._recommendations[existing_id] = recommendation.model_copy(update={
                        "id": existing_id,
                        "updated_at": datetime.now(timezone.utc)
                    })
                    return self._recommendations[existing_id].model_copy()

            self._recommendations[recommendation.id] = recommendation
            if recommendation.fingerprint:
                self._fingerprints[recommendation.fingerprint] = recommendation.id

            prod_id = recommendation.unified_product_id
            if prod_id not in self._product_recommendations:
                self._product_recommendations[prod_id] = []
            if recommendation.id not in self._product_recommendations[prod_id]:
                self._product_recommendations[prod_id].append(recommendation.id)

            return recommendation.model_copy()

    def batch_save_recommendations(self, recommendations: List[ProductRecommendation]) -> List[ProductRecommendation]:
        saved = []
        for r in recommendations:
            saved.append(self.save_recommendation(r))
        return saved

    def get_recommendation(self, recommendation_id: str) -> Optional[ProductRecommendation]:
        with self._lock:
            rec = self._recommendations.get(recommendation_id)
            return rec.model_copy() if rec else None

    def get_recommendation_by_fingerprint(self, fingerprint: str) -> Optional[ProductRecommendation]:
        with self._lock:
            rec_id = self._fingerprints.get(fingerprint)
            if rec_id and rec_id in self._recommendations:
                return self._recommendations[rec_id].model_copy()
            return None

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
    ) -> List[ProductRecommendation]:
        with self._lock:
            res = list(self._recommendations.values())

            if unified_product_id:
                res = [r for r in res if r.unified_product_id == unified_product_id or r.target_product_id == unified_product_id]
            if recommendation_type:
                res = [r for r in res if r.recommendation_type.lower() == recommendation_type.lower()]
            if category:
                res = [r for r in res if r.category and category.lower() in r.category.lower()]
            if brand:
                res = [r for r in res if r.brand and brand.lower() in r.brand.lower()]
            if platform:
                res = [r for r in res if any(p.lower() == platform.lower() for p in r.platforms)]
            if status:
                res = [r for r in res if r.status == status]
            if min_score is not None:
                res = [r for r in res if r.score >= min_score]
            if min_confidence is not None:
                res = [r for r in res if r.confidence >= min_confidence]
            if search:
                s_lower = search.lower()
                res = [
                    r for r in res
                    if (r.category and s_lower in r.category.lower())
                    or (r.brand and s_lower in r.brand.lower())
                    or any(s_lower in reason.lower() for reason in r.reasons)
                    or (s_lower in r.unified_product_id.lower())
                ]

            if sort_by == "score_desc":
                res.sort(key=lambda x: x.score, reverse=True)
            elif sort_by == "score_asc":
                res.sort(key=lambda x: x.score)
            elif sort_by == "confidence_desc":
                res.sort(key=lambda x: x.confidence, reverse=True)
            elif sort_by == "created_at_desc":
                res.sort(key=lambda x: x.created_at, reverse=True)
            else:
                res.sort(key=lambda x: x.created_at, reverse=True)

            return [r.model_copy() for r in res[offset:offset + limit]]

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
    ) -> int:
        recs = self.list_recommendations(
            unified_product_id=unified_product_id,
            recommendation_type=recommendation_type,
            category=category,
            brand=brand,
            platform=platform,
            status=status,
            min_score=min_score,
            min_confidence=min_confidence,
            search=search,
            limit=10000,
            offset=0
        )
        return len(recs)

    def list_recommendations_for_product(
        self,
        unified_product_id: str,
        recommendation_type: Optional[str] = None,
        limit: int = 10
    ) -> List[ProductRecommendation]:
        return self.list_recommendations(
            unified_product_id=unified_product_id,
            recommendation_type=recommendation_type,
            status="active",
            limit=limit,
            sort_by="score_desc"
        )

    def create_candidate(self, candidate: RecommendationCandidate) -> RecommendationCandidate:
        with self._lock:
            self._candidates[candidate.id] = candidate
            return candidate.model_copy()

    def get_candidate(self, candidate_id: str) -> Optional[RecommendationCandidate]:
        with self._lock:
            c = self._candidates.get(candidate_id)
            return c.model_copy() if c else None

    def list_candidates(
        self,
        status: Optional[str] = None,
        candidate_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[RecommendationCandidate]:
        with self._lock:
            res = list(self._candidates.values())
            if status:
                res = [c for c in res if c.status == status]
            if candidate_type:
                res = [c for c in res if c.candidate_type.lower() == candidate_type.lower()]
            res.sort(key=lambda x: x.created_at, reverse=True)
            return [c.model_copy() for c in res[offset:offset + limit]]

    def resolve_candidate(
        self,
        candidate_id: str,
        status: str,
        reviewed_by: Optional[str] = None
    ) -> Optional[RecommendationCandidate]:
        with self._lock:
            if candidate_id not in self._candidates:
                return None
            c = self._candidates[candidate_id]
            updated = c.model_copy(update={
                "status": status,
                "reviewed_by": reviewed_by,
                "reviewed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })
            self._candidates[candidate_id] = updated
            return updated.model_copy()

    def record_interaction(self, interaction: RecommendationInteraction) -> RecommendationInteraction:
        with self._lock:
            self._interactions.append(interaction)
            return interaction.model_copy()

    def list_interactions(
        self,
        user_id: Optional[str] = None,
        product_id: Optional[str] = None,
        interaction_type: Optional[str] = None,
        limit: int = 50
    ) -> List[RecommendationInteraction]:
        with self._lock:
            res = list(self._interactions)
            if user_id:
                res = [i for i in res if i.user_id == user_id]
            if product_id:
                res = [i for i in res if i.product_id == product_id]
            if interaction_type:
                res = [i for i in res if i.interaction_type == interaction_type]
            res.sort(key=lambda x: x.occurred_at, reverse=True)
            return [i.model_copy() for i in res[:limit]]

    def record_audit(self, audit: RecommendationAudit) -> RecommendationAudit:
        with self._lock:
            self._audits.append(audit)
            return audit.model_copy()

    def list_audits(
        self,
        product_id: Optional[str] = None,
        agent_id: str = "agent_recommendation_engine",
        limit: int = 50
    ) -> List[RecommendationAudit]:
        with self._lock:
            res = [a for a in self._audits if a.agent_id == agent_id]
            if product_id:
                res = [a for a in res if a.product_id == product_id]
            res.sort(key=lambda x: x.created_at, reverse=True)
            return [a.model_copy() for a in res[:limit]]

    def get_recommendation_stats(self) -> AgentRecommendationStats:
        with self._lock:
            all_recs = list(self._recommendations.values())
            active_recs = [r for r in all_recs if r.status == "active"]
            best_value = [r for r in active_recs if r.recommendation_type == "best_value"]
            trending = [r for r in active_recs if r.recommendation_type == "trending_product"]
            cross_plat = [r for r in active_recs if r.recommendation_type == "cross_platform"]
            pending_cands = [c for c in self._candidates.values() if c.status == "pending"]

            by_type: Dict[str, int] = {}
            by_cat: Dict[str, int] = {}
            for r in active_recs:
                by_type[r.recommendation_type] = by_type.get(r.recommendation_type, 0) + 1
                if r.category:
                    by_cat[r.category] = by_cat.get(r.category, 0) + 1

            int_by_type: Dict[str, int] = {}
            for i in self._interactions:
                int_by_type[i.interaction_type] = int_by_type.get(i.interaction_type, 0) + 1

            return AgentRecommendationStats(
                total_recommendations=len(all_recs),
                active_recommendations_count=len(active_recs),
                best_value_count=len(best_value),
                trending_recommendations_count=len(trending),
                cross_platform_count=len(cross_plat),
                candidates_pending_review=len(pending_cands),
                total_interactions_logged=len(self._interactions),
                recommendations_by_type=by_type,
                recommendations_by_category=by_cat,
                interactions_by_type=int_by_type,
                last_updated=datetime.now(timezone.utc)
            )

    def upsert_memory(self, memory: AIAgentMemory) -> AIAgentMemory:
        with self._lock:
            key = f"{memory.agent_id}:{memory.memory_type}:{memory.memory_key}"
            self._memories[key] = memory.model_copy()
            return self._memories[key].model_copy()

    def get_memory(self, agent_id: str, memory_type: str, memory_key: str) -> Optional[AIAgentMemory]:
        with self._lock:
            key = f"{agent_id}:{memory_type}:{memory_key}"
            mem = self._memories.get(key)
            return mem.model_copy() if mem else None

    def list_memories(self, agent_id: str, memory_type: Optional[str] = None) -> List[AIAgentMemory]:
        with self._lock:
            res = [m for m in self._memories.values() if m.agent_id == agent_id]
            if memory_type:
                res = [m for m in res if m.memory_type == memory_type]
            res.sort(key=lambda x: x.last_observed_at, reverse=True)
            return [m.model_copy() for m in res]

    def record_memory_event(self, event: AIAgentMemoryEvent) -> AIAgentMemoryEvent:
        with self._lock:
            self._memory_events.append(event.model_copy())
            return event.model_copy()

    def list_memory_events(self, agent_id: str, memory_id: Optional[str] = None) -> List[AIAgentMemoryEvent]:
        with self._lock:
            res = [e for e in self._memory_events if e.agent_id == agent_id]
            if memory_id:
                res = [e for e in res if e.memory_id == memory_id]
            res.sort(key=lambda x: x.created_at, reverse=True)
            return [e.model_copy() for e in res]

    def clear(self):
        with self._lock:
            self._recommendations.clear()
            self._product_recommendations.clear()
            self._fingerprints.clear()
            self._candidates.clear()
            self._interactions.clear()
            self._audits.clear()
            self._memories.clear()
            self._memory_events.clear()


class InMemoryMarketOpportunityRepository(MarketOpportunityRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._opportunities: Dict[str, MarketOpportunity] = {}
        self._product_opportunities: Dict[str, List[str]] = {} # unified_product_id -> list of opp_ids
        self._category_opportunities: Dict[str, List[str]] = {} # category -> list of opp_ids
        self._fingerprints: Dict[str, str] = {} # fingerprint -> opp_id
        self._candidates: Dict[str, MarketOpportunityCandidate] = {}
        self._audits: List[MarketOpportunityAudit] = []
        self._memories: Dict[str, AIAgentMemory] = {}
        self._memory_events: List[AIAgentMemoryEvent] = []

    def save_opportunity(self, opportunity: MarketOpportunity) -> MarketOpportunity:
        with self._lock:
            # Check fingerprint for duplicate prevention
            if opportunity.fingerprint and opportunity.fingerprint in self._fingerprints:
                existing_id = self._fingerprints[opportunity.fingerprint]
                if existing_id in self._opportunities:
                    self._opportunities[existing_id] = opportunity.model_copy(update={
                        "id": existing_id,
                        "updated_at": datetime.now(timezone.utc)
                    })
                    return self._opportunities[existing_id].model_copy()

            self._opportunities[opportunity.id] = opportunity.model_copy()
            if opportunity.fingerprint:
                self._fingerprints[opportunity.fingerprint] = opportunity.id

            if opportunity.unified_product_id:
                if opportunity.unified_product_id not in self._product_opportunities:
                    self._product_opportunities[opportunity.unified_product_id] = []
                if opportunity.id not in self._product_opportunities[opportunity.unified_product_id]:
                    self._product_opportunities[opportunity.unified_product_id].append(opportunity.id)

            if opportunity.category:
                cat_k = opportunity.category.strip().lower()
                if cat_k not in self._category_opportunities:
                    self._category_opportunities[cat_k] = []
                if opportunity.id not in self._category_opportunities[cat_k]:
                    self._category_opportunities[cat_k].append(opportunity.id)

            return opportunity.model_copy()

    def get_opportunity(self, id: str) -> Optional[MarketOpportunity]:
        with self._lock:
            opp = self._opportunities.get(id)
            return opp.model_copy() if opp else None

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
    ) -> List[MarketOpportunity]:
        with self._lock:
            opps = list(self._opportunities.values())

            if unified_product_id:
                opps = [o for o in opps if o.unified_product_id == unified_product_id]
            if opportunity_type and opportunity_type != "all":
                opps = [o for o in opps if o.opportunity_type == opportunity_type]
            if category and category != "all":
                c_low = category.strip().lower()
                opps = [o for o in opps if o.category and c_low in o.category.strip().lower()]
            if brand and brand != "all":
                b_low = brand.strip().lower()
                opps = [o for o in opps if o.brand and b_low in o.brand.strip().lower()]
            if platform and platform != "all":
                plat_low = platform.strip().lower()
                opps = [o for o in opps if any(plat_low in p.strip().lower() for p in (o.current_platforms + o.missing_observed_platforms))]
            if status and status != "all":
                opps = [o for o in opps if o.status == status]
            if min_score is not None:
                opps = [o for o in opps if o.score >= min_score]
            if min_confidence is not None:
                opps = [o for o in opps if o.confidence >= min_confidence]
            if search and search.strip():
                s_low = search.strip().lower()
                opps = [
                    o for o in opps
                    if (o.unified_product_id and s_low in o.unified_product_id.lower())
                    or (o.category and s_low in o.category.lower())
                    or (o.brand and s_low in o.brand.lower())
                    or any(s_low in r.lower() for r in o.reasons)
                ]

            if sort_by == "score_asc":
                opps.sort(key=lambda x: x.score)
            elif sort_by == "confidence_desc":
                opps.sort(key=lambda x: x.confidence, reverse=True)
            elif sort_by == "oldest":
                opps.sort(key=lambda x: x.detected_at)
            else:
                # Default: score desc, then detected_at desc
                opps.sort(key=lambda x: (x.score, x.detected_at), reverse=True)

            return [o.model_copy() for o in opps[offset:offset + limit]]

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
    ) -> int:
        return len(self.list_opportunities(
            unified_product_id=unified_product_id,
            opportunity_type=opportunity_type,
            category=category,
            brand=brand,
            platform=platform,
            status=status,
            min_score=min_score,
            min_confidence=min_confidence,
            search=search,
            limit=100000,
            offset=0
        ))

    def list_opportunities_for_product(self, unified_product_id: str) -> List[MarketOpportunity]:
        with self._lock:
            opp_ids = self._product_opportunities.get(unified_product_id, [])
            res = [self._opportunities[oid].model_copy() for oid in opp_ids if oid in self._opportunities]
            res.sort(key=lambda x: x.score, reverse=True)
            return res

    def list_opportunities_for_category(self, category: str) -> List[MarketOpportunity]:
        with self._lock:
            cat_k = category.strip().lower()
            opp_ids = self._category_opportunities.get(cat_k, [])
            res = [self._opportunities[oid].model_copy() for oid in opp_ids if oid in self._opportunities]
            res.sort(key=lambda x: x.score, reverse=True)
            return res

    def create_candidate(self, candidate: MarketOpportunityCandidate) -> MarketOpportunityCandidate:
        with self._lock:
            self._candidates[candidate.id] = candidate.model_copy()
            return candidate.model_copy()

    def get_candidate(self, id: str) -> Optional[MarketOpportunityCandidate]:
        with self._lock:
            c = self._candidates.get(id)
            return c.model_copy() if c else None

    def list_candidates(
        self,
        status: Optional[str] = None,
        candidate_type: Optional[str] = None,
        limit: int = 50
    ) -> List[MarketOpportunityCandidate]:
        with self._lock:
            cands = list(self._candidates.values())
            if status and status != "all":
                cands = [c for c in cands if c.status == status]
            if candidate_type and candidate_type != "all":
                cands = [c for c in cands if c.candidate_type == candidate_type]
            cands.sort(key=lambda x: x.created_at, reverse=True)
            return [c.model_copy() for c in cands[:limit]]

    def resolve_candidate(
        self,
        candidate_id: str,
        status: str,
        reviewed_by: Optional[str] = None
    ) -> Optional[MarketOpportunityCandidate]:
        with self._lock:
            if candidate_id not in self._candidates:
                return None
            cand = self._candidates[candidate_id]
            updated = cand.model_copy(update={
                "status": status,
                "reviewed_by": reviewed_by,
                "reviewed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })
            self._candidates[candidate_id] = updated
            return updated.model_copy()

    def record_audit(self, audit: MarketOpportunityAudit) -> MarketOpportunityAudit:
        with self._lock:
            self._audits.append(audit.model_copy())
            return audit.model_copy()

    def list_audits(
        self,
        product_id: Optional[str] = None,
        opportunity_id: Optional[str] = None,
        agent_id: str = "agent_market_opportunity_intelligence",
        limit: int = 50
    ) -> List[MarketOpportunityAudit]:
        with self._lock:
            res = [a for a in self._audits if a.agent_id == agent_id]
            if product_id:
                res = [a for a in res if a.evidence.get("unified_product_id") == product_id or a.opportunity_id == product_id]
            if opportunity_id:
                res = [a for a in res if a.opportunity_id == opportunity_id]
            res.sort(key=lambda x: x.created_at, reverse=True)
            return [a.model_copy() for a in res[:limit]]

    def get_opportunity_stats(self) -> AgentMarketOpportunityStats:
        with self._lock:
            all_opps = list(self._opportunities.values())
            active_opps = [o for o in all_opps if o.status == "active"]
            high_conf = [o for o in active_opps if o.confidence >= 0.90]
            high_score = [o for o in active_opps if o.score >= 80.0]
            pending_cands = [c for c in self._candidates.values() if c.status == "pending"]
            confirmed_cands = [c for c in self._candidates.values() if c.status == "approved"]
            dismissed_cands = [c for c in self._candidates.values() if c.status in ("dismissed", "rejected")]

            by_type: Dict[str, int] = {}
            by_cat: Dict[str, int] = {}
            by_plat: Dict[str, int] = {}

            for o in active_opps:
                by_type[o.opportunity_type] = by_type.get(o.opportunity_type, 0) + 1
                if o.category:
                    by_cat[o.category] = by_cat.get(o.category, 0) + 1
                for p in o.current_platforms + o.missing_observed_platforms:
                    by_plat[p] = by_plat.get(p, 0) + 1

            return AgentMarketOpportunityStats(
                total_opportunities=len(all_opps),
                active_opportunities_count=len(active_opps),
                high_confidence_count=len(high_conf),
                high_score_count=len(high_score),
                pending_review_count=len(pending_cands),
                confirmed_count=len(confirmed_cands),
                dismissed_count=len(dismissed_cands),
                opportunities_by_type=by_type,
                opportunities_by_category=by_cat,
                opportunities_by_platform=by_plat,
                last_updated=datetime.now(timezone.utc)
            )

    def upsert_memory(self, memory: AIAgentMemory) -> AIAgentMemory:
        with self._lock:
            key = f"{memory.agent_id}:{memory.memory_type}:{memory.memory_key}"
            self._memories[key] = memory.model_copy()
            return self._memories[key].model_copy()

    def get_memory(self, agent_id: str, memory_type: str, memory_key: str) -> Optional[AIAgentMemory]:
        with self._lock:
            key = f"{agent_id}:{memory_type}:{memory_key}"
            mem = self._memories.get(key)
            return mem.model_copy() if mem else None

    def list_memories(self, agent_id: str, memory_type: Optional[str] = None) -> List[AIAgentMemory]:
        with self._lock:
            res = [m for m in self._memories.values() if m.agent_id == agent_id]
            if memory_type:
                res = [m for m in res if m.memory_type == memory_type]
            res.sort(key=lambda x: x.last_observed_at, reverse=True)
            return [m.model_copy() for m in res]

    def record_memory_event(self, event: AIAgentMemoryEvent) -> AIAgentMemoryEvent:
        with self._lock:
            self._memory_events.append(event.model_copy())
            return event.model_copy()

    def list_memory_events(self, agent_id: str, memory_id: Optional[str] = None) -> List[AIAgentMemoryEvent]:
        with self._lock:
            res = [e for e in self._memory_events if e.agent_id == agent_id]
            if memory_id:
                res = [e for e in res if e.memory_id == memory_id]
            res.sort(key=lambda x: x.created_at, reverse=True)
            return [e.model_copy() for e in res]

    def clear(self):
        with self._lock:
            self._opportunities.clear()
            self._product_opportunities.clear()
            self._category_opportunities.clear()
            self._fingerprints.clear()
            self._candidates.clear()
            self._audits.clear()
            self._memories.clear()
            self._memory_events.clear()


class InMemoryScraperRepository(ScraperRepository):
    def __init__(self, storage_file: Optional[str] = None):
        self._lock = threading.RLock()
        self._jobs: Dict[str, ScraperCrawlJob] = {}
        self._raw_payloads: Dict[str, RawScrapedPayload] = {}  # key: f"{marketplace}:{product_id}"
        self._health: Dict[str, ScraperMarketplaceHealth] = {}
        self._init_defaults()

    def _init_defaults(self):
        now = datetime.now(timezone.utc)
        defaults = ["daraz", "amazon", "ebay", "aliexpress", "shopify"]
        for m in defaults:
            self._health[m] = ScraperMarketplaceHealth(
                marketplace=m,
                status="healthy",
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                challenge_count=0,
                average_latency_ms=0.0
            )

    def create_job(self, job: ScraperCrawlJob) -> ScraperCrawlJob:
        with self._lock:
            self._jobs[job.id] = job.model_copy()
            return job.model_copy()

    def get_job(self, job_id: str) -> Optional[ScraperCrawlJob]:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.model_copy() if job else None

    def update_job(self, job: ScraperCrawlJob) -> ScraperCrawlJob:
        with self._lock:
            self._jobs[job.id] = job.model_copy(update={"updated_at": datetime.now(timezone.utc)})
            return self._jobs[job.id].model_copy()

    def list_jobs(
        self,
        marketplace: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ScraperCrawlJob]:
        with self._lock:
            res = list(self._jobs.values())
            if marketplace and marketplace != "all":
                res = [j for j in res if j.marketplace.lower() == marketplace.lower()]
            if status and status != "all":
                res = [j for j in res if j.status.lower() == status.lower()]
            res.sort(key=lambda j: j.created_at, reverse=True)
            return [j.model_copy() for j in res[offset:offset + limit]]

    def count_jobs(
        self,
        marketplace: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        with self._lock:
            res = list(self._jobs.values())
            if marketplace and marketplace != "all":
                res = [j for j in res if j.marketplace.lower() == marketplace.lower()]
            if status and status != "all":
                res = [j for j in res if j.status.lower() == status.lower()]
            return len(res)

    def save_raw_payload(self, payload: RawScrapedPayload) -> RawScrapedPayload:
        with self._lock:
            key = f"{payload.marketplace.lower()}:{payload.product_id.strip()}"
            self._raw_payloads[key] = payload.model_copy()
            return payload.model_copy()

    def get_raw_payload(self, marketplace: str, product_id: str) -> Optional[RawScrapedPayload]:
        with self._lock:
            key = f"{marketplace.lower()}:{product_id.strip()}"
            p = self._raw_payloads.get(key)
            return p.model_copy() if p else None

    def list_raw_payloads(
        self,
        marketplace: Optional[str] = None,
        crawl_job_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[RawScrapedPayload]:
        with self._lock:
            res = list(self._raw_payloads.values())
            if marketplace and marketplace != "all":
                res = [p for p in res if p.marketplace.lower() == marketplace.lower()]
            if crawl_job_id:
                res = [p for p in res if p.crawl_job_id == crawl_job_id]
            res.sort(key=lambda p: p.scraped_at, reverse=True)
            return [p.model_copy() for p in res[offset:offset + limit]]

    def record_marketplace_health(self, health: ScraperMarketplaceHealth) -> ScraperMarketplaceHealth:
        with self._lock:
            self._health[health.marketplace.lower()] = health.model_copy()
            return health.model_copy()

    def get_marketplace_health(self, marketplace: str) -> Optional[ScraperMarketplaceHealth]:
        with self._lock:
            h = self._health.get(marketplace.lower())
            return h.model_copy() if h else None

    def list_marketplace_health(self) -> List[ScraperMarketplaceHealth]:
        with self._lock:
            return [h.model_copy() for h in self._health.values()]

    def clear(self):
        with self._lock:
            self._jobs.clear()
            self._raw_payloads.clear()
            self._init_defaults()


# Singleton In-Memory Repository Instances
user_repo = InMemoryUserRepository()
workspace_repo = InMemoryWorkspaceRepository()
product_repo = InMemoryProductRepository()
category_repo = InMemoryCategoryRepository()
platform_repo = InMemoryPlatformRepository()
watchlist_repo = InMemoryWatchlistRepository()
alert_repo = InMemoryAlertRepository()
notification_repo = InMemoryNotificationRepository()
report_repo = InMemoryReportRepository()
data_source_repo = InMemoryDataSourceRepository()
settings_repo = InMemorySettingsRepository()
auth_persistence_repo = InMemoryAuthPersistenceRepository()
subscription_repo = InMemorySubscriptionRepository()
credit_repo = InMemoryCreditRepository()
marketplace_product_repo = InMemoryMarketplaceProductRepository()
shopify_repo = InMemoryShopifyRepository()
unified_product_repo = InMemoryUnifiedProductRepository()
llm_usage_repo = InMemoryLLMUsageRepository()
data_quality_repo = InMemoryDataQualityRepository()
taxonomy_repo = InMemoryTaxonomyRepository()
trend_detection_repo = InMemoryTrendDetectionRepository()
anomaly_detection_repo = InMemoryAnomalyDetectionRepository()
recommendation_repo = InMemoryRecommendationRepository()
market_opportunity_repo = InMemoryMarketOpportunityRepository()
scraper_repo = InMemoryScraperRepository()


class InMemoryMarketIntelligenceRepository(MarketIntelligenceRepository):
    """Thread-safe in-memory repository for Phase 3 Market Intelligence and Social Signals."""

    def __init__(self):
        self._lock = threading.RLock()
        self._snapshots: Dict[str, MarketIntelligenceSnapshot] = {}
        self._social_signals: Dict[str, SocialSignal] = {}

    def save_snapshot(self, snapshot: MarketIntelligenceSnapshot) -> MarketIntelligenceSnapshot:
        with self._lock:
            self._snapshots[snapshot.id] = snapshot.model_copy()
            return snapshot.model_copy()

    def get_latest_snapshot(self, product_id: str, marketplace: Optional[str] = None) -> Optional[MarketIntelligenceSnapshot]:
        with self._lock:
            matches = [
                s for s in self._snapshots.values()
                if s.product_id == product_id and (not marketplace or s.marketplace.lower() == marketplace.lower())
            ]
            if not matches:
                return None
            matches.sort(key=lambda x: x.calculated_at or x.created_at, reverse=True)
            return matches[0].model_copy()

    def list_snapshots(
        self,
        product_id: Optional[str] = None,
        marketplace: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[MarketIntelligenceSnapshot]:
        with self._lock:
            items = list(self._snapshots.values())
            if product_id:
                items = [s for s in items if s.product_id == product_id]
            if marketplace and marketplace.lower() != "all":
                items = [s for s in items if s.marketplace.lower() == marketplace.lower()]
            items.sort(key=lambda x: x.calculated_at or x.created_at, reverse=True)
            return [s.model_copy() for s in items[offset:offset + limit]]

    def save_social_signal(self, signal: SocialSignal) -> SocialSignal:
        with self._lock:
            self._social_signals[signal.id] = signal.model_copy()
            return signal.model_copy()

    def list_social_signals(
        self,
        platform: Optional[str] = None,
        product_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[SocialSignal]:
        with self._lock:
            items = list(self._social_signals.values())
            if platform and platform.lower() != "all":
                items = [s for s in items if s.platform.lower() == platform.lower()]
            if product_id:
                items = [s for s in items if s.matched_product_id == product_id or s.matched_unified_id == product_id]
            items.sort(key=lambda x: x.observed_at or x.created_at, reverse=True)
            return [s.model_copy() for s in items[offset:offset + limit]]

    def clear(self):
        with self._lock:
            self._snapshots.clear()
            self._social_signals.clear()


market_intelligence_repo = InMemoryMarketIntelligenceRepository()












