from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.models.domain import User, UserSettings, UserSettingsUpdate
from backend.app.repositories.base import SettingsRepository, UserRepository
from backend.app.api.deps import get_settings_repository, get_user_repository, get_current_user
from backend.app.schemas.common import ResponseModel

router = APIRouter()

@router.get("", response_model=ResponseModel[UserSettings])
def get_settings(
    current_user: User = Depends(get_current_user),
    settings: SettingsRepository = Depends(get_settings_repository)
):
    st = settings.get_by_user_id(current_user.id)
    if not st:
        st = UserSettings(
            user_id=current_user.id,
            full_name=current_user.full_name,
            email=current_user.email,
            avatar_url=current_user.avatar_url,
            role=current_user.role,
        )
        settings.update(st)
    else:
        # Keep profile fields in sync with authoritative current_user
        modified = False
        if st.full_name != current_user.full_name:
            st.full_name = current_user.full_name
            modified = True
        if st.email != current_user.email:
            st.email = current_user.email
            modified = True
        if st.role != current_user.role:
            st.role = current_user.role
            modified = True
        if st.avatar_url != current_user.avatar_url:
            st.avatar_url = current_user.avatar_url
            modified = True
        if modified:
            settings.update(st)

    return ResponseModel(
        success=True,
        message="Settings retrieved successfully",
        data=st
    )

@router.put("", response_model=ResponseModel[UserSettings])
@router.patch("", response_model=ResponseModel[UserSettings])
def update_settings(
    payload: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    settings: SettingsRepository = Depends(get_settings_repository),
    users: UserRepository = Depends(get_user_repository)
):
    # 1. Load existing or initialize
    st = settings.get_by_user_id(current_user.id)
    if not st:
        st = UserSettings(
            user_id=current_user.id,
            full_name=current_user.full_name,
            email=current_user.email,
            avatar_url=current_user.avatar_url,
            role=current_user.role,
        )

    # 2. Validate and apply updates
    if payload.full_name is not None:
        clean_name = payload.full_name.strip()
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
        st.full_name = clean_name
        current_user.full_name = clean_name

    if payload.email is not None:
        clean_email = payload.email.strip()
        if not clean_email or "@" not in clean_email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Valid email address is required"
            )
        st.email = clean_email
        current_user.email = clean_email

    if payload.avatar_url is not None:
        st.avatar_url = payload.avatar_url
        current_user.avatar_url = payload.avatar_url

    if payload.role is not None:
        st.role = payload.role
        current_user.role = payload.role

    if payload.company_name is not None:
        st.company_name = payload.company_name
    if payload.timezone is not None:
        st.timezone = payload.timezone
    if payload.currency is not None:
        st.currency = payload.currency
    if payload.email_notifications is not None:
        st.email_notifications = payload.email_notifications
    if payload.alert_critical_only is not None:
        st.alert_critical_only = payload.alert_critical_only
    if payload.weekly_digest is not None:
        st.weekly_digest = payload.weekly_digest
    if payload.ai_model_preference is not None:
        st.ai_model_preference = payload.ai_model_preference
    if payload.ai_confidence_threshold is not None:
        st.ai_confidence_threshold = payload.ai_confidence_threshold
    if payload.auto_generate_reports is not None:
        st.auto_generate_reports = payload.auto_generate_reports
    if payload.dark_mode is not None:
        st.dark_mode = payload.dark_mode
    if payload.table_dense_view is not None:
        st.table_dense_view = payload.table_dense_view
    if payload.live_ticker_enabled is not None:
        st.live_ticker_enabled = payload.live_ticker_enabled

    st.user_id = current_user.id

    # 3. Persist in both SettingsRepository and UserRepository
    saved_settings = settings.update(st)
    users.update(current_user)

    return ResponseModel(
        success=True,
        message="Settings updated successfully",
        data=saved_settings
    )
