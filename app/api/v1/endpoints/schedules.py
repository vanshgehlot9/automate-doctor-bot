from fastapi import APIRouter, Depends, HTTPException, Header, Query
from app.api.deps import get_current_user, CurrentUser
from typing import List
from datetime import date
from app.schemas.schedule import (
    DoctorScheduleCreate,
    DoctorScheduleInDB,
    DoctorHolidayCreate,
    DoctorHolidayInDB,
    AppointmentSlotBase
)
from app.services.schedule_service import ScheduleService

router = APIRouter()

@router.post("/", response_model=DoctorScheduleInDB)
def create_schedule(schedule_in: DoctorScheduleCreate, current_user: CurrentUser = Depends(get_current_user)):
    """
    Create a new schedule rule for a doctor.
    """
    if schedule_in.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return ScheduleService.create_schedule(current_user.tenant_id, schedule_in)

@router.get("/{doctor_id}", response_model=List[DoctorScheduleInDB])
def get_doctor_schedules(doctor_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """
    Get all schedule rules for a doctor.
    """
    return ScheduleService.get_doctor_schedules(current_user.tenant_id, doctor_id)

@router.post("/holidays", response_model=DoctorHolidayInDB)
def create_holiday(holiday_in: DoctorHolidayCreate, current_user: CurrentUser = Depends(get_current_user)):
    """
    Create a new holiday/leave for a doctor.
    """
    if holiday_in.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return ScheduleService.create_holiday(holiday_in)

@router.get("/{doctor_id}/slots", response_model=List[AppointmentSlotBase])
def get_available_slots(
    doctor_id: str, 
    target_date: date = Query(..., description="Target date in YYYY-MM-DD format"),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Dynamically generates and returns available slots for a given doctor on a specific date,
    accounting for existing locked/booked appointments, breaks, and holidays.
    """
    return ScheduleService.get_available_slots(current_user.tenant_id, doctor_id, target_date)
