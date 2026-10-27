"""Report generation endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from apps.core.security import get_current_user
from apps.dto.api_resp import APIResponse
from apps.dto.summary_dto import SummaryRequest
from apps.services.summary_data_service import SummaryDataService
from apps.services.activity_export_service import ActivityExportService
from apps.modules.ai_summary.summary_service import SummaryEngine

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("", response_model=APIResponse)
def list_reports(current_user: dict = Depends(get_current_user)):
    reports = SummaryDataService.get_summaries(current_user["user_id"], limit=50)
    return APIResponse(data=reports)


@router.post("/generate", response_model=APIResponse)
def generate_report(request: SummaryRequest, current_user: dict = Depends(get_current_user)):
    engine = SummaryEngine(current_user["user_id"])
    result = engine.generate_summary(summary_type=request.summary_type)
    
    if result.get("status") == "error":
        return APIResponse(success=False, message=result.get("message", "Error"), statusCode=500)
        
    return APIResponse(data=result, message="Summary generated successfully")


@router.get("/export", response_model=APIResponse)
def export_activity(
    current_user: dict = Depends(get_current_user),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    try:
        result = ActivityExportService.export_activity(
            current_user["user_id"],
            start_date=start_date,
            end_date=end_date,
        )
        return APIResponse(data=result, message="Activity exported to markdown successfully")
    except Exception as exc:
        return APIResponse(success=False, message=str(exc), statusCode=500)
