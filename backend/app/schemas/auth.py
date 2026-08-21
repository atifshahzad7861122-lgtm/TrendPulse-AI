from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    terms_accepted: bool

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
    remember_me: bool = False

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    is_verified: bool
    workspace_id: Optional[str] = None
    role: str

class VerifyEmailRequest(BaseModel):
    token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)

class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_verified: bool
    workspace_id: Optional[str] = None
    role: str
    avatar_url: Optional[str] = None
