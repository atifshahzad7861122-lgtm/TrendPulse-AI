import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from backend.app.core.security import (
    verify_password, get_password_hash, create_access_token, generate_random_token
)
from backend.app.models.domain import (
    User, Workspace, WorkspaceMember, UserSession, EmailVerification, PasswordResetToken, LoginEvent, UserSettings,
    UserSubscription
)
from backend.app.repositories.base import (
    UserRepository, WorkspaceRepository, AuthPersistenceRepository, SettingsRepository,
    SubscriptionRepository, CreditRepository
)
from backend.app.schemas.auth import (
    UserRegisterRequest, UserLoginRequest, TokenResponse,
    VerifyEmailRequest, ForgotPasswordRequest, ResetPasswordRequest, UserProfileResponse
)

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

class AuthService:
    def __init__(
        self,
        users: UserRepository,
        workspaces: WorkspaceRepository,
        auth_persistence: AuthPersistenceRepository,
        settings: SettingsRepository,
        subscriptions: Optional[SubscriptionRepository] = None,
        credits: Optional[CreditRepository] = None
    ):
        self.users = users
        self.workspaces = workspaces
        self.auth_persistence = auth_persistence
        self.settings = settings
        self.subscriptions = subscriptions
        self.credits = credits


    def register(
        self,
        req: UserRegisterRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        if req.password != req.confirm_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")
        if not req.terms_accepted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Terms and conditions must be accepted")

        existing = self.users.get_by_email(req.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

        user_id = f"usr_{uuid.uuid4().hex[:8]}"
        workspace_id = f"ws_{uuid.uuid4().hex[:8]}"
        verification_token = generate_random_token(16)
        now = datetime.now(timezone.utc)

        # 1. User
        new_user = User(
            id=user_id,
            email=req.email,
            full_name=req.full_name,
            hashed_password=get_password_hash(req.password),
            is_active=True,
            is_verified=False,
            verification_token=verification_token,
            workspace_id=workspace_id,
            role="Administrator",
            created_at=now
        )
        self.users.create(new_user)

        # 2. Workspace
        first_name = req.full_name.split()[0] if req.full_name else "My"
        new_ws = Workspace(
            id=workspace_id,
            name=f"{first_name}'s Workspace",
            industry="General E-Commerce",
            use_case="Market Intelligence",
            currency="USD",
            default_dashboard="signals",
            connected_sources=["daraz", "tiktok", "instagram"],
            is_setup_complete=False,
            owner_id=user_id,
            created_at=now
        )
        self.workspaces.create(new_ws)

        # 3. Workspace Member
        member = WorkspaceMember(
            id=f"wsm_{uuid.uuid4().hex[:8]}",
            workspace_id=workspace_id,
            user_id=user_id,
            role="Administrator",
            created_at=now
        )
        self.workspaces.add_member(member)

        # 4. User Settings
        new_settings = UserSettings(
            user_id=user_id,
            full_name=req.full_name,
            email=req.email,
            role="Administrator",
            company_name=f"{first_name} Commerce",
            timezone="UTC",
            currency="USD",
            email_notifications=True,
            alert_critical_only=False,
            weekly_digest=True,
            ai_model_preference="Qwen 2.5 Max (Simulated)",
            ai_confidence_threshold=80,
            auto_generate_reports=False,
            dark_mode=True,
            table_dense_view=False,
            live_ticker_enabled=True
        )
        self.settings.update(new_settings)

        # 5. Email Verification Record
        verification = EmailVerification(
            id=f"ev_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            token=verification_token,
            expires_at=now + timedelta(hours=24),
            created_at=now
        )
        self.auth_persistence.create_email_verification(verification)

        # 6. Default Free Subscription & Credit Allocation
        if self.subscriptions:
            free_plan = self.subscriptions.get_plan_by_slug("free")
            plan_id = free_plan.id if free_plan else "plan_free"
            sub = UserSubscription(
                id=f"sub_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                plan_id=plan_id,
                status="active",
                started_at=now,
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
                created_at=now,
                updated_at=now
            )
            self.subscriptions.create_user_subscription(sub)

        if self.credits:
            acc = self.credits.get_or_create_account(user_id)
            if self.subscriptions and free_plan and free_plan.monthly_credits > 0:
                self.credits.update_account_balance(
                    user_id=user_id,
                    new_balance=free_plan.monthly_credits,
                    delta_granted=free_plan.monthly_credits,
                    delta_used=0
                )

        # 7. Audit Event
        self.auth_persistence.record_login_event(
            LoginEvent(
                id=f"evt_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                email=req.email,
                event_type="registered",
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_json={"workspace_id": workspace_id},
                created_at=now
            )
        )


        return {
            "user_id": user_id,
            "email": req.email,
            "verification_token": verification_token,
            "dev_verification_url": f"/verify-email?token={verification_token}"
        }

    def login(
        self,
        req: UserLoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> TokenResponse:
        now = datetime.now(timezone.utc)
        user = self.users.get_by_email(req.email)
        if not user or not verify_password(req.password, user.hashed_password):
            self.auth_persistence.record_login_event(
                LoginEvent(
                    id=f"evt_{uuid.uuid4().hex[:8]}",
                    user_id=user.id if user else None,
                    email=req.email,
                    event_type="login_failed",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata_json={"reason": "invalid_credentials"},
                    created_at=now
                )
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        if not user.is_active:
            self.auth_persistence.record_login_event(
                LoginEvent(
                    id=f"evt_{uuid.uuid4().hex[:8]}",
                    user_id=user.id,
                    email=req.email,
                    event_type="login_failed",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata_json={"reason": "account_inactive"},
                    created_at=now
                )
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

        # Update last login timestamp
        user.last_login_at = now
        self.users.update(user)

        # Generate JWT & Session
        access_token = create_access_token(user.id)
        token_hash = _hash_token(access_token)
        session = UserSession(
            id=f"sess_{uuid.uuid4().hex[:8]}",
            user_id=user.id,
            token_hash=token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            is_revoked=False,
            expires_at=now + timedelta(days=7),
            created_at=now
        )
        self.auth_persistence.create_session(session)

        # Audit Event
        self.auth_persistence.record_login_event(
            LoginEvent(
                id=f"evt_{uuid.uuid4().hex[:8]}",
                user_id=user.id,
                email=user.email,
                event_type="login_success",
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_json={"session_id": session.id},
                created_at=now
            )
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_verified=user.is_verified,
            workspace_id=user.workspace_id,
            role=user.role
        )

    def logout(
        self,
        token: Optional[str] = None,
        current_user: Optional[User] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        if token:
            token_hash = _hash_token(token)
            self.auth_persistence.revoke_session(token_hash)

        if current_user:
            self.auth_persistence.record_login_event(
                LoginEvent(
                    id=f"evt_{uuid.uuid4().hex[:8]}",
                    user_id=current_user.id,
                    email=current_user.email,
                    event_type="logout",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata_json={},
                    created_at=now
                )
            )
        return {}

    def verify_email(
        self,
        token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        ev = self.auth_persistence.get_email_verification(token)
        user = self.users.get_by_verification_token(token) if not ev else self.users.get_by_id(ev.user_id)

        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token")

        if ev:
            if ev.used_at is not None or ev.expires_at < now:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token")
            self.auth_persistence.mark_email_verification_used(token)

        user.is_verified = True
        user.verification_token = None
        self.users.update(user)

        self.auth_persistence.record_login_event(
            LoginEvent(
                id=f"evt_{uuid.uuid4().hex[:8]}",
                user_id=user.id,
                email=user.email,
                event_type="email_verified",
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_json={},
                created_at=now
            )
        )

        access_token = create_access_token(user.id)
        return {
            "access_token": access_token,
            "user_id": user.id,
            "is_verified": True,
            "workspace_id": user.workspace_id
        }

    def forgot_password(
        self,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        user = self.users.get_by_email(email)
        if not user:
            # Generic anti-enumeration response
            self.auth_persistence.record_login_event(
                LoginEvent(
                    id=f"evt_{uuid.uuid4().hex[:8]}",
                    user_id=None,
                    email=email,
                    event_type="forgot_password_unknown",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata_json={},
                    created_at=now
                )
            )
            return {
                "email": email,
                "message": "If the email exists, a password reset link has been generated."
            }

        reset_token = generate_random_token(16)
        expires_at = now + timedelta(hours=1)

        # Store reset token record
        prt = PasswordResetToken(
            id=f"prt_{uuid.uuid4().hex[:8]}",
            user_id=user.id,
            token=reset_token,
            expires_at=expires_at,
            created_at=now
        )
        self.auth_persistence.create_password_reset_token(prt)

        user.reset_token = reset_token
        user.reset_token_expires_at = expires_at
        self.users.update(user)

        self.auth_persistence.record_login_event(
            LoginEvent(
                id=f"evt_{uuid.uuid4().hex[:8]}",
                user_id=user.id,
                email=user.email,
                event_type="forgot_password_requested",
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_json={"reset_token_id": prt.id},
                created_at=now
            )
        )

        return {
            "email": email,
            "reset_token": reset_token,
            "dev_reset_url": f"/reset-password?token={reset_token}"
        }

    def reset_password(
        self,
        token: str,
        new_password: str,
        confirm_password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        if new_password != confirm_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

        now = datetime.now(timezone.utc)
        prt = self.auth_persistence.get_password_reset_token(token)
        user = self.users.get_by_reset_token(token) if not prt else self.users.get_by_id(prt.user_id)

        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

        if prt:
            if prt.used_at is not None or prt.expires_at < now:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
            self.auth_persistence.mark_password_reset_token_used(token)
        elif user.reset_token_expires_at and user.reset_token_expires_at < now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

        user.hashed_password = get_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expires_at = None
        self.users.update(user)

        # Revoke existing sessions upon password reset for security
        self.auth_persistence.revoke_all_user_sessions(user.id)

        self.auth_persistence.record_login_event(
            LoginEvent(
                id=f"evt_{uuid.uuid4().hex[:8]}",
                user_id=user.id,
                email=user.email,
                event_type="password_reset_success",
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_json={},
                created_at=now
            )
        )

        return {"email": user.email}
