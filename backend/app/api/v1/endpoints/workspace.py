from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.models.domain import User, Workspace
from backend.app.repositories.base import WorkspaceRepository
from backend.app.api.deps import get_workspace_repository, get_current_user
from backend.app.schemas.entities import WorkspaceSetupRequest, WorkspaceResponse
from backend.app.schemas.common import ResponseModel

router = APIRouter()

@router.get("", response_model=ResponseModel[WorkspaceResponse])
def get_workspace(
    current_user: User = Depends(get_current_user),
    workspaces: WorkspaceRepository = Depends(get_workspace_repository)
):
    ws = workspaces.get_by_owner_id(current_user.id)
    if not ws and current_user.workspace_id:
        ws = workspaces.get_by_id(current_user.workspace_id)
    if not ws:
        # Create default workspace if none
        ws = Workspace(
            id=f"ws_{current_user.id[:8]}",
            name=f"{current_user.full_name}'s Workspace",
            industry="Consumer Tech & Retail",
            use_case="Market Intelligence",
            owner_id=current_user.id,
            is_setup_complete=False
        )
        workspaces.create(ws)
    
    return ResponseModel(
        success=True,
        message="Workspace retrieved",
        data=WorkspaceResponse(
            id=ws.id,
            name=ws.name,
            industry=ws.industry,
            use_case=ws.use_case,
            currency=ws.currency,
            default_dashboard=ws.default_dashboard,
            connected_sources=ws.connected_sources,
            is_setup_complete=ws.is_setup_complete,
            owner_id=ws.owner_id
        )
    )

@router.post("/setup", response_model=ResponseModel[WorkspaceResponse])
def setup_workspace(
    req: WorkspaceSetupRequest,
    current_user: User = Depends(get_current_user),
    workspaces: WorkspaceRepository = Depends(get_workspace_repository)
):
    ws = workspaces.get_by_owner_id(current_user.id)
    if not ws and current_user.workspace_id:
        ws = workspaces.get_by_id(current_user.workspace_id)
    
    if not ws:
        ws = Workspace(
            id=f"ws_{current_user.id[:8]}",
            name=req.name,
            industry=req.industry,
            use_case=req.use_case,
            currency=req.currency,
            default_dashboard=req.default_dashboard,
            connected_sources=req.data_sources,
            is_setup_complete=True,
            owner_id=current_user.id
        )
        workspaces.create(ws)
    else:
        ws.name = req.name
        ws.industry = req.industry
        ws.use_case = req.use_case
        ws.currency = req.currency
        ws.default_dashboard = req.default_dashboard
        ws.connected_sources = req.data_sources
        ws.is_setup_complete = True
        workspaces.update(ws)
    
    return ResponseModel(
        success=True,
        message="Workspace setup completed successfully",
        data=WorkspaceResponse(
            id=ws.id,
            name=ws.name,
            industry=ws.industry,
            use_case=ws.use_case,
            currency=ws.currency,
            default_dashboard=ws.default_dashboard,
            connected_sources=ws.connected_sources,
            is_setup_complete=ws.is_setup_complete,
            owner_id=ws.owner_id
        )
    )
