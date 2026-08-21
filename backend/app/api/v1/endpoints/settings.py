from fastapi import APIRouter, Depends
from backend.app.models.domain import User, UserSettings
from backend.app.repositories.base import SettingsRepository
from backend.app.api.deps import get_settings_repository, get_current_user
from backend.app.schemas.common import ResponseModel

router = APIRouter()

@router.get("", response_model=ResponseModel[UserSettings])
def get_settings(
    current_user: User = Depends(get_current_user),
    settings: SettingsRepository = Depends(get_settings_repository)
):
    st = settings.get_by_user_id(current_user.id)
    return ResponseModel(
        success=True,
        message="Settings retrieved successfully",
        data=st
    )

@router.put("", response_model=ResponseModel[UserSettings])
def update_settings(
    updated_settings: UserSettings,
    current_user: User = Depends(get_current_user),
    settings: SettingsRepository = Depends(get_settings_repository)
):
    updated_settings.user_id = current_user.id
    saved = settings.update(updated_settings)
    return ResponseModel(
        success=True,
        message="Settings updated successfully",
        data=saved
    )
