from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import PlainTextResponse
from backend.app.models.domain import Report, User
from backend.app.services.report_service import ReportService
from backend.app.api.deps import get_report_service, get_current_user
from backend.app.schemas.entities import ReportGenerateRequest
from backend.app.schemas.common import ResponseModel

router = APIRouter()

@router.get("", response_model=ResponseModel[List[Report]])
def list_reports(report_service: ReportService = Depends(get_report_service)):
    items = report_service.list_reports()
    return ResponseModel(
        success=True,
        message="Reports retrieved successfully",
        data=items
    )

@router.get("/{report_id}", response_model=ResponseModel[Report])
def get_report_detail(
    report_id: str,
    report_service: ReportService = Depends(get_report_service)
):
    r = report_service.get_report_by_id(report_id)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return ResponseModel(
        success=True,
        message="Report detail retrieved",
        data=r
    )

@router.post("/generate", response_model=ResponseModel[Report])
def generate_report(
    req: ReportGenerateRequest,
    report_service: ReportService = Depends(get_report_service),
    current_user: User = Depends(get_current_user)
):
    new_rep = report_service.generate_report(req, current_user)
    return ResponseModel(
        success=True,
        message="Report generated successfully",
        data=new_rep
    )

@router.get("/{report_id}/export")
def export_report(
    report_id: str,
    format: str = "json",
    report_service: ReportService = Depends(get_report_service)
):
    data = report_service.export_report_data(report_id, format_=format)
    if data is None:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if format.lower() == "csv":
        return PlainTextResponse(
            content=data,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="report_{report_id}.csv"'}
        )

    return data
