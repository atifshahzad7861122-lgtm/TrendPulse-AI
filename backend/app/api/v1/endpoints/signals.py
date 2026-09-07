import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, Query
from backend.app.schemas.signals import LiveSignalsResponse
from backend.app.services.live_signal_service import LiveSignalService
from backend.app.api.deps import get_live_signal_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/live")
def get_live_signals(
    limit: int = Query(default=20, ge=1, le=50, description="Max number of live signals to retrieve"),
    signal_service: LiveSignalService = Depends(get_live_signal_service)
):
    """
    Returns real-time factual market signals extracted from connected marketplace sources.
    Platform-neutral architecture supporting Daraz, YouTube, TikTok, and other platforms.
    """
    try:
        response_data = signal_service.get_live_signals(limit=limit)
        return {
            "success": True,
            "data": response_data.model_dump()
        }
    except Exception as e:
        logger.error(f"Error serving live signals feed: {e}")
        return {
            "success": False,
            "message": "Live market signals currently unavailable.",
            "data": {
                "signals": [],
                "total": 0
            }
        }
