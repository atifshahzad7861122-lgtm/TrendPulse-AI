import threading
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from backend.app.core.security import get_password_hash
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
                product_count=428,
                avg_trend_score=92.4,
                growth_rate=245.8,
                velocity_label="Explosive",
                top_platforms=["TikTok", "Instagram"],
                description="Color-changing cosmetics, barrier repair serums, and thermal skincare formulas leading growth."
            ),
            Category(
                id="cat_sports",
                name="Sports & Outdoor",
                slug="sports",
                product_count=312,
                avg_trend_score=89.6,
                growth_rate=194.2,
                velocity_label="Breakout",
                top_platforms=["YouTube", "TikTok"],
                description="Ergonomic running gear, hydration systems, and micro-mobility accessories gaining strong momentum."
            ),
            Category(
                id="cat_electronics",
                name="Consumer Electronics",
                slug="electronics",
                product_count=580,
                avg_trend_score=88.1,
                growth_rate=162.0,
                velocity_label="Surging",
                top_platforms=["Daraz", "YouTube", "TikTok"],
                description="Modular MagSafe stands, ergonomic desk peripherals, and portable cooling hardware."
            ),
            Category(
                id="cat_home",
                name="Home & Kitchen",
                slug="home-kitchen",
                product_count=290,
                avg_trend_score=84.5,
                growth_rate=135.0,
                velocity_label="Steady",
                top_platforms=["Instagram", "TikTok"],
                description="Aesthetic beverage tools, matcha preparation sets, and atmospheric lighting."
            ),
            Category(
                id="cat_fashion",
                name="Fashion & Apparel",
                slug="fashion",
                product_count=510,
                avg_trend_score=86.2,
                growth_rate=152.4,
                velocity_label="Surging",
                top_platforms=["TikTok", "Instagram"],
                description="Technical streetwear, seamless activewear sets, and retro-minimalist accessories."
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
                id="plt_tiktok",
                name="TikTok",
                slug="tiktok",
                icon="tiktok",
                total_signals=842000,
                active_trends=142,
                velocity_growth=48.2,
                market_share=38.5,
                status="Connected",
                recent_spikes=[
                    {"hashtag": "#HydroGlow", "growth": "+420%", "signals": "184K"},
                    {"hashtag": "#RunClubAesthetic", "growth": "+210%", "signals": "92K"},
                    {"hashtag": "#DeskUpgrade", "growth": "+165%", "signals": "74K"}
                ]
            ),
            PlatformMetrics(
                id="plt_daraz",
                name="Daraz",
                slug="daraz",
                icon="shopping_bag",
                total_signals=512000,
                active_trends=98,
                velocity_growth=32.4,
                market_share=26.0,
                status="Connected",
                recent_spikes=[
                    {"hashtag": "MagSnap Stand", "growth": "+195%", "signals": "112K"},
                    {"hashtag": "Neck Fan Pro", "growth": "+140%", "signals": "86K"},
                    {"hashtag": "Thermal Serum", "growth": "+230%", "signals": "64K"}
                ]
            ),
            PlatformMetrics(
                id="plt_instagram",
                name="Instagram",
                slug="instagram",
                icon="photo_camera",
                total_signals=420000,
                active_trends=86,
                velocity_growth=26.8,
                market_share=20.5,
                status="Connected",
                recent_spikes=[
                    {"hashtag": "#MatchaRitual", "growth": "+175%", "signals": "78K"},
                    {"hashtag": "#SunsetLampDecor", "growth": "+130%", "signals": "62K"},
                    {"hashtag": "#CleanBeauty", "growth": "+210%", "signals": "95K"}
                ]
            ),
            PlatformMetrics(
                id="plt_youtube",
                name="YouTube",
                slug="youtube",
                icon="smart_display",
                total_signals=290000,
                active_trends=54,
                velocity_growth=19.5,
                market_share=15.0,
                status="Disconnected",
                recent_spikes=[
                    {"hashtag": "Running Gear 2026", "growth": "+240%", "signals": "88K"},
                    {"hashtag": "Top Desk Gadgets", "growth": "+155%", "signals": "58K"}
                ]
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
        now = datetime.now(timezone.utc)
        reps = [
            Report(
                id="rep_01",
                title="Executive Market Intelligence Briefing - Q2 Peak",
                template="executive",
                time_range="30d",
                status="Ready",
                progress=100,
                category="All Categories",
                platforms=["TikTok", "Daraz", "Instagram", "YouTube"],
                key_findings=[
                    "Thermal cosmetics and activewear hydration systems are exhibiting >200% acceleration rate.",
                    "Consumer price tolerance has stabilized at $25 - $45 band for viral aesthetic products.",
                    "Daraz platform search-to-buy velocity is highest in modular electronic accessories."
                ],
                ai_takeaways="Emerging demand signals point toward high-utility aesthetic crossovers. Sellers with localized inventory in South Asian fulfillment hubs will capture 40% margin premiums over cross-border dropshippers.",
                total_signals_analyzed=482000,
                high_conviction_count=18,
                created_by="Alex Vance",
                created_at=now - timedelta(days=2)
            ),
            Report(
                id="rep_02",
                title="Beauty & Skincare Velocity Surge Analysis",
                template="velocity_surge",
                time_range="7d",
                status="Ready",
                progress=100,
                category="Beauty & Personal Care",
                platforms=["TikTok", "Instagram"],
                key_findings=[
                    "Color-shift thermal lip cosmetics generated 1.2M views in 72 hours.",
                    "Review sentiment scores average 92% positive with low return complaints.",
                    "Major domestic retail chains have not yet stocked thermal serum alternatives."
                ],
                ai_takeaways="First-mover supplier window is estimated at 3 to 5 weeks before market saturation occurs.",
                total_signals_analyzed=124000,
                high_conviction_count=6,
                created_by="Alex Vance",
                created_at=now - timedelta(days=5)
            )
        ]
        for r in reps:
            self._reports[r.id] = r

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
                id="src_tiktok",
                name="TikTok Social Intelligence",
                slug="tiktok",
                icon="tiktok",
                description="Monitors video engagement, hashtag velocity, and creator mentions.",
                status="Connected",
                last_sync=now - timedelta(minutes=18),
                sync_frequency="Real-time (15 min)",
                records_synced=842150,
                health_score=99
            ),
            DataSource(
                id="src_daraz",
                name="Daraz Marketplace Scraper",
                slug="daraz",
                icon="shopping_bag",
                description="Tracks real-time pricing, stock changes, sales velocity, and seller ratings.",
                status="Connected",
                last_sync=now - timedelta(minutes=32),
                sync_frequency="Hourly",
                records_synced=512800,
                health_score=97
            ),
            DataSource(
                id="src_instagram",
                name="Instagram Trends Graph",
                slug="instagram",
                icon="photo_camera",
                description="Ingests reels audio surges, lifestyle carousel trends, and brand tagging.",
                status="Connected",
                last_sync=now - timedelta(hours=1),
                sync_frequency="Hourly",
                records_synced=420600,
                health_score=95
            ),
            DataSource(
                id="src_youtube",
                name="YouTube Long-form & Shorts API",
                slug="youtube",
                icon="smart_display",
                description="Analyzes in-depth review velocity, unboxing trends, and comment intent.",
                status="Disconnected",
                last_sync=None,
                sync_frequency="Daily",
                records_synced=0,
                health_score=0
            ),
            DataSource(
                id="src_facebook",
                name="Facebook Marketplace & Groups",
                slug="facebook",
                icon="group",
                description="Monitors localized buying demand and peer-to-peer commerce listings.",
                status="Disconnected",
                last_sync=None,
                sync_frequency="Daily",
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


