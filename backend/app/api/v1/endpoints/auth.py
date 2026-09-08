from typing import Optional
from datetime import datetime, timedelta, timezone
from jose import jwt
from fastapi import APIRouter, Depends, Request, Header, HTTPException, status
from backend.app.core.config import settings
from backend.app.models.domain import User
from backend.app.services.auth_service import AuthService
from backend.app.repositories.base import UserRepository, SettingsRepository
from backend.app.api.deps import get_auth_service, get_current_user, get_user_repository, get_settings_repository, oauth2_scheme
from backend.app.schemas.auth import (
    UserRegisterRequest, UserLoginRequest, TokenResponse,
    VerifyEmailRequest, ResendVerificationRequest, ForgotPasswordRequest, ResetPasswordRequest,
    UserProfileResponse, UserProfileUpdateRequest
)
from backend.app.schemas.common import ResponseModel

router = APIRouter()

def _get_client_info(request: Request):
    ip = request.client.host if request.client else None
    agent = request.headers.get("user-agent")
    return ip, agent

@router.post("/demo-session", response_model=ResponseModel[TokenResponse])
def create_demo_session(request: Request):
    """
    Creates a temporary read-only demo session for hackathon evaluation.
    Only available when DEMO_MODE=True.
    """
    if not getattr(settings, "DEMO_MODE", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public demo mode is currently disabled."
        )

    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    demo_user_id = getattr(settings, "DEMO_USER_ID", "usr_demo_101")
    demo_email = getattr(settings, "DEMO_USER_EMAIL", "judge@trendpulse.demo")
    demo_workspace_id = getattr(settings, "DEMO_WORKSPACE_ID", "ws_demo_101")

    payload = {
        "sub": demo_user_id,
        "email": demo_email,
        "role": "demo",
        "is_demo": True,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return ResponseModel(
        success=True,
        message="Demo session initialized successfully",
        data=TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=demo_user_id,
            email=demo_email,
            full_name="Hackathon Judge (Demo Mode)",
            is_verified=True,
            workspace_id=demo_workspace_id,
            role="demo",
            avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80"
        )
    )

@router.post("/register", response_model=ResponseModel[dict])
def register(
    req: UserRegisterRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    ip, agent = _get_client_info(request)
    data = auth_service.register(req, ip_address=ip, user_agent=agent)
    return ResponseModel(
        success=True,
        message="Registration successful. Please verify your email.",
        data=data
    )

@router.post("/login", response_model=ResponseModel[TokenResponse])
def login(
    req: UserLoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    ip, agent = _get_client_info(request)
    token_resp = auth_service.login(req, ip_address=ip, user_agent=agent)
    return ResponseModel(
        success=True,
        message="Login successful",
        data=token_resp
    )

@router.post("/logout", response_model=ResponseModel[dict])
def logout(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
):
    ip, agent = _get_client_info(request)
    data = auth_service.logout(token=token, ip_address=ip, user_agent=agent)
    return ResponseModel(
        success=True,
        message="Successfully logged out",
        data=data
    )

@router.post("/verify-email", response_model=ResponseModel[dict])
def verify_email(
    req: VerifyEmailRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    ip, agent = _get_client_info(request)
    data = auth_service.verify_email(req.token, email=req.email, ip_address=ip, user_agent=agent)
    return ResponseModel(
        success=True,
        message="Email verified successfully. Proceed to workspace setup.",
        data=data
    )

@router.post("/resend-verification", response_model=ResponseModel[dict])
def resend_verification(
    req: ResendVerificationRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    ip, agent = _get_client_info(request)
    data = auth_service.resend_verification(req.email, ip_address=ip, user_agent=agent)
    return ResponseModel(
        success=True,
        message="If the email exists and is unverified, a new verification code has been sent.",
        data=data
    )

@router.post("/forgot-password", response_model=ResponseModel[dict])
def forgot_password(
    req: ForgotPasswordRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    ip, agent = _get_client_info(request)
    data = auth_service.forgot_password(req.email, ip_address=ip, user_agent=agent)
    return ResponseModel(
        success=True,
        message="If the email exists, a password reset link has been generated.",
        data=data
    )

@router.post("/reset-password", response_model=ResponseModel[dict])
def reset_password(
    req: ResetPasswordRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    ip, agent = _get_client_info(request)
    data = auth_service.reset_password(
        token=req.token,
        new_password=req.new_password,
        confirm_password=req.confirm_password,
        ip_address=ip,
        user_agent=agent
    )
    return ResponseModel(
        success=True,
        message="Password has been reset successfully. Please log in.",
        data=data
    )

@router.get("/me", response_model=ResponseModel[UserProfileResponse])
def get_me(current_user: User = Depends(get_current_user)):
    return ResponseModel(
        success=True,
        message="User profile retrieved",
        data=UserProfileResponse(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            is_verified=current_user.is_verified,
            workspace_id=current_user.workspace_id,
            role=current_user.role,
            avatar_url=current_user.avatar_url
        )
    )

@router.patch("/me", response_model=ResponseModel[UserProfileResponse])
@router.put("/me", response_model=ResponseModel[UserProfileResponse])
def update_me(
    req: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    users: UserRepository = Depends(get_user_repository),
    settings: SettingsRepository = Depends(get_settings_repository)
):
    if req.full_name is not None:
        clean_name = req.full_name.strip()
        if not clean_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Full name cannot be empty"
            )
        if len(clean_name) > 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Full name cannot exceed 100 characters"
            )
        current_user.full_name = clean_name

    if req.email is not None:
        clean_email = req.email.strip()
        if not clean_email or "@" not in clean_email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Valid email address is required"
            )
        current_user.email = clean_email

    if req.avatar_url is not None:
        current_user.avatar_url = req.avatar_url

    if req.role is not None:
        current_user.role = req.role

    # 1. Update user repository
    updated_user = users.update(current_user)

    # 2. Sync user settings repository
    st = settings.get_by_user_id(current_user.id)
    if not st:
        st = UserSettings(
            user_id=current_user.id,
            full_name=current_user.full_name,
            email=current_user.email,
            avatar_url=current_user.avatar_url,
            role=current_user.role,
        )
    else:
        if req.full_name is not None:
            st.full_name = current_user.full_name
        if req.email is not None:
            st.email = current_user.email
        if req.avatar_url is not None:
            st.avatar_url = current_user.avatar_url
        if req.role is not None:
            st.role = current_user.role
    settings.update(st)

    return ResponseModel(
        success=True,
        message="User profile updated successfully",
        data=UserProfileResponse(
            id=updated_user.id,
            email=updated_user.email,
            full_name=updated_user.full_name,
            is_verified=updated_user.is_verified,
            workspace_id=updated_user.workspace_id,
            role=updated_user.role,
            avatar_url=updated_user.avatar_url
        )
    )

