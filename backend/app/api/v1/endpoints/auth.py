from typing import Optional
from fastapi import APIRouter, Depends, Request, Header
from backend.app.models.domain import User
from backend.app.services.auth_service import AuthService
from backend.app.api.deps import get_auth_service, get_current_user, oauth2_scheme
from backend.app.schemas.auth import (
    UserRegisterRequest, UserLoginRequest, TokenResponse,
    VerifyEmailRequest, ForgotPasswordRequest, ResetPasswordRequest, UserProfileResponse
)
from backend.app.schemas.common import ResponseModel

router = APIRouter()

def _get_client_info(request: Request):
    ip = request.client.host if request.client else None
    agent = request.headers.get("user-agent")
    return ip, agent

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
    data = auth_service.verify_email(req.token, ip_address=ip, user_agent=agent)
    return ResponseModel(
        success=True,
        message="Email verified successfully. Proceed to workspace setup.",
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
