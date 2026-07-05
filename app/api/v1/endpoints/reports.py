"""
Medical Reports REST API
Endpoints for upload, timeline, search, compare.
All endpoints require authentication and are fully tenant-isolated.
"""
from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List
from app.api.deps import get_current_user, CurrentUser
from app.schemas.report import (
    MedicalReportCreate,
    MedicalReportInDB,
    MedicalReportUpdate,
    ReportSearchRequest,
    ReportCompareRequest,
    ReportStatus,
)
from app.services.report_service import ReportService

router = APIRouter()


@router.post("/upload", response_model=MedicalReportInDB)
async def upload_report(
    background_tasks: BackgroundTasks,
    patient_id: str = Form(...),
    doctor_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Upload a medical report image or PDF. Triggers background AI processing."""
    t_id = current_user.tenant_id
    contents = await file.read()

    report_in = MedicalReportCreate(
        patient_id=patient_id,
        doctor_id=doctor_id,
        status=ReportStatus.PENDING,
        uploaded_by=current_user.uid,
        wa_mime_type=file.content_type,
    )
    report = ReportService.create_report(t_id, report_in)

    # Save raw bytes to Supabase Storage if available, else store inline
    try:
        from app.db.supabase import db as _sb
        storage_path = f"reports/{t_id}/{report.id}/{file.filename}"
        _sb.storage.from_("reports").upload(storage_path, contents, {"content-type": file.content_type})
        file_url = _sb.storage.from_("reports").get_public_url(storage_path)
        ReportService.update_report(t_id, report.id, MedicalReportUpdate(file_url=file_url))
    except Exception:
        pass  # Storage not configured; URL will remain empty

    # Kick off AI processing in background
    background_tasks.add_task(
        ReportService.process_report_async,
        t_id, report.id, contents, file.content_type or "image/jpeg"
    )
    return report


@router.get("/patients/{patient_id}", response_model=List[MedicalReportInDB])
def get_patient_reports(
    patient_id: str,
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Return all reports for a patient in chronological (newest-first) order."""
    return ReportService.get_patient_reports(current_user.tenant_id, patient_id, limit)


@router.get("/{report_id}", response_model=MedicalReportInDB)
def get_report(
    report_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a single report by ID."""
    report = ReportService.get_report(current_user.tenant_id, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/search", response_model=List[MedicalReportInDB])
def search_reports(
    req: ReportSearchRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Search reports by keyword (matches tags, report type, OCR text)."""
    return ReportService.search_reports(current_user.tenant_id, req.patient_id, req.query, req.limit)


@router.post("/compare")
def compare_reports(
    req: ReportCompareRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Use AI to compare two reports and explain parameter trends."""
    comparison = ReportService.compare_reports(current_user.tenant_id, req.report_id_1, req.report_id_2)
    return {"comparison": comparison}
