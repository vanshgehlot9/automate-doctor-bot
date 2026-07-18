from fastapi import APIRouter, Depends, HTTPException, Header
from app.api.deps import get_current_user, CurrentUser
from typing import List, Optional
from app.schemas.doctor import DoctorCreate, DoctorUpdate, DoctorInDB
from app.services.doctor_service import DoctorService
from app.db.supabase import db
from app.db.retry import with_retry
from datetime import datetime

router = APIRouter()

@router.post("/", response_model=DoctorInDB)
def create_doctor(doctor_in: DoctorCreate, current_user: CurrentUser = Depends(get_current_user)):
    """
    Create a new doctor.
    Supports whatsapp_number field so the doctor can be identified in the WhatsApp bot.
    """
    doctor = DoctorService.create_doctor(current_user.tenant_id, doctor_in)
    if not doctor:
        raise HTTPException(status_code=500, detail="Failed to create doctor")
    return doctor

@router.get("/", response_model=List[DoctorInDB])
def get_all_doctors(current_user: CurrentUser = Depends(get_current_user)):
    """
    List all doctors for a tenant.
    """
    print(f"DEBUG: get_all_doctors called with tenant_id: {current_user.tenant_id}")
    return DoctorService.get_all_doctors(current_user.tenant_id)

@router.get("/{doctor_id}", response_model=DoctorInDB)
def get_doctor(doctor_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """
    Get doctor by ID.
    """
    doctor = DoctorService.get_doctor(current_user.tenant_id, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor

@router.put("/{doctor_id}", response_model=DoctorInDB)
def update_doctor(
    doctor_id: str,
    doctor_in: DoctorUpdate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Update doctor profile including whatsapp_number.
    Only hospital_admin or super_admin may update doctors.
    """
    if current_user.active_role not in ("hospital_admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Not authorized to update doctors")

    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")

    update_data = doctor_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided to update")

    update_data["updated_at"] = datetime.utcnow().isoformat()

    try:
        response = with_retry(
            lambda: db.table("doctors")
            .update(update_data)
            .eq("tenant_id", current_user.tenant_id)
            .eq("id", doctor_id)
            .execute()
        )()
        if not response.data:
            raise HTTPException(status_code=404, detail="Doctor not found")
        return DoctorInDB(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update doctor: {str(e)}")

@router.delete("/{doctor_id}")
def delete_doctor(doctor_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """
    Delete doctor by ID.
    """
    success = DoctorService.delete_doctor(current_user.tenant_id, doctor_id)
    if not success:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return {"success": True, "message": "Doctor deleted successfully"}
