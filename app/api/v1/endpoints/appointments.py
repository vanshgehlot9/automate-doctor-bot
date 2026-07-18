from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.schemas.appointment import AppointmentCreate, AppointmentInDB, AppointmentStatus, AppointmentUpdate
from app.services.appointment_service import AppointmentService
from app.api.deps import get_current_user, CurrentUser

router = APIRouter()

@router.post("/", response_model=AppointmentInDB)
def create_appointment(appointment_in: AppointmentCreate, current_user: CurrentUser = Depends(get_current_user)):
    """
    Create a new appointment.
    """
    appointment = AppointmentService.create_appointment(current_user.tenant_id, appointment_in)
    if not appointment:
        raise HTTPException(status_code=500, detail="Failed to create appointment")
    return appointment

@router.get("/{appointment_id}", response_model=AppointmentInDB)
def get_appointment(appointment_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """
    Get appointment by ID.
    """
    appointment = AppointmentService.get_appointment(current_user.tenant_id, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment

@router.patch("/{appointment_id}/status", response_model=AppointmentInDB)
def update_appointment_status(appointment_id: str, status: AppointmentStatus, current_user: CurrentUser = Depends(get_current_user)):
    """
    Update the status of an appointment.
    """
    appointment = AppointmentService.update_appointment_status(current_user.tenant_id, appointment_id, status)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found or failed to update")
    return appointment

@router.get("/", response_model=List[AppointmentInDB])
def get_all_appointments(current_user: CurrentUser = Depends(get_current_user)):
    """
    List all appointments for a tenant.
    """
    return AppointmentService.get_all_appointments(current_user.tenant_id)

@router.get("/{appointment_id}/calendar.ics")
def get_appointment_calendar(appointment_id: str):
    """
    Generate an ICS file for the appointment natively.
    """
    from fastapi.responses import Response
    from app.db.supabase import db
    from datetime import datetime, timedelta
    
    try:
        res = db.table("appointments").select("*, doctors(name)").eq("id", appointment_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Appointment not found")
            
        appt = res.data[0]
        
        dt_start_str = f"{appt.get('appointment_date')} {appt.get('appointment_time')}"
        dt_start_local = datetime.strptime(dt_start_str, "%Y-%m-%d %H:%M:%S")
        dt_start_utc = dt_start_local - timedelta(minutes=330)
        
        if appt.get("appointment_end"):
            dt_end_str = f"{appt.get('appointment_date')} {appt.get('appointment_end')}"
            dt_end_local = datetime.strptime(dt_end_str, "%Y-%m-%d %H:%M:%S")
        else:
            dt_end_local = dt_start_local + timedelta(minutes=30)
        dt_end_utc = dt_end_local - timedelta(minutes=330)
            
        fmt_start = dt_start_utc.strftime("%Y%m%dT%H%M%SZ")
        fmt_end = dt_end_utc.strftime("%Y%m%dT%H%M%SZ")
        now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        
        doctor_name = appt.get("doctors", {}).get("name") or "Doctor"
        summary = f"Appointment with Dr. {doctor_name}"
        
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//DoctorBot//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:{appointment_id}@doctorbot.com",
            f"DTSTAMP:{now}",
            f"DTSTART:{fmt_start}",
            f"DTEND:{fmt_end}",
            f"SUMMARY:{summary}",
            "END:VEVENT",
            "END:VCALENDAR"
        ]
        ics = "\r\n".join(lines) + "\r\n"
        
        return Response(content=ics, media_type="text/calendar")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
