from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from backend.app.models.domain import DataSource
from backend.app.domain.signals import IngestionResult
from backend.app.services.data_sources_service import DataSourceService
from backend.app.services.ingestion_service import IngestionPipeline
from backend.app.connectors.youtube_connector import YouTubeDataConnector
from backend.app.api.deps import get_data_source_service, get_ingestion_pipeline
from backend.app.schemas.common import ResponseModel
from backend.app.core.config import settings

router = APIRouter()

@router.get("", response_model=ResponseModel[List[DataSource]])
def list_data_sources(source_service: DataSourceService = Depends(get_data_source_service)):
    items = source_service.list_sources()
    return ResponseModel(
        success=True,
        message="Data sources retrieved successfully",
        data=items
    )

@router.get("/config/status", response_model=ResponseModel[Dict[str, Any]])
def get_data_sources_config_status():
    """
    Safely reports whether live external APIs are configured without leaking any credentials.
    """
    yt_connector = YouTubeDataConnector()
    is_yt_live = yt_connector.is_live_configured

    return ResponseModel(
        success=True,
        message="Data source configuration status retrieved",
        data={
            "youtube": {
                "is_live_configured": is_yt_live,
                "mode": "LIVE" if is_yt_live else "MOCK",
                "max_results": settings.YOUTUBE_MAX_RESULTS,
                "region_code": settings.YOUTUBE_REGION_CODE,
                "language": settings.YOUTUBE_LANGUAGE
            },
            "platforms": {
                "youtube": {"type": "real_api", "status": "CONNECTED" if is_yt_live else "AVAILABLE", "live": is_yt_live},
                "instagram": {"type": "unconnected", "status": "COMING_SOON", "live": False},
                "tiktok": {"type": "unconnected", "status": "COMING_SOON", "live": False},
                "facebook": {"type": "unconnected", "status": "COMING_SOON", "live": False},
                "daraz": {"type": "scraper_engine", "status": "CONNECTED", "live": True},
            },
            "environment": settings.ENVIRONMENT
        }
    )

@router.post("/{slug}/connect", response_model=ResponseModel[DataSource])
def connect_data_source(
    slug: str,
    source_service: DataSourceService = Depends(get_data_source_service)
):
    s = source_service.connect_source(slug)
    if not s:
        raise HTTPException(status_code=404, detail="Data source not found")
    return ResponseModel(
        success=True,
        message=f"{s.name} connected successfully",
        data=s
    )

@router.post("/{slug}/disconnect", response_model=ResponseModel[DataSource])
def disconnect_data_source(
    slug: str,
    source_service: DataSourceService = Depends(get_data_source_service)
):
    s = source_service.disconnect_source(slug)
    if not s:
        raise HTTPException(status_code=404, detail="Data source not found")
    return ResponseModel(
        success=True,
        message=f"{s.name} disconnected successfully",
        data=s
    )

@router.post("/{slug}/sync", response_model=ResponseModel[IngestionResult])
def sync_data_source(
    slug: str,
    ingestion: IngestionPipeline = Depends(get_ingestion_pipeline)
):
    result = ingestion.sync_source(slug)
    if result.status == "Failed":
        raise HTTPException(status_code=400, detail=result.errors[0] if result.errors else "Sync failed")
    
    mode_str = "LIVE" if result.is_live else "MOCK"
    return ResponseModel(
        success=True,
        message=f"[{mode_str}] Sync completed for {slug.title()}: {result.records_normalized} signals normalized, {result.records_matched} matched, {result.records_updated} products updated.",
        data=result
    )

@router.post("/sync-all", response_model=ResponseModel[dict])
def sync_all_connectors(
    ingestion: IngestionPipeline = Depends(get_ingestion_pipeline)
):
    summary = ingestion.sync_all()
    return ResponseModel(
        success=True,
        message=f"Successfully ingested {summary['total_records']} signals across active channels.",
        data=summary
    )
