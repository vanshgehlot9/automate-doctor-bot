from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from enum import Enum

class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked-in"
    IN_CONSULTATION = "in consultation"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no show"

class AppointmentBase(BaseModel):
    patient_id: str
    doctor_id: str
    appointment_date: date
    appointment_time: str # Start time, e.g., "10:30"
    appointment_end: str # End time, e.g., "10:45"
    slot_id: Optional[str] = None
    reason_for_visit: str
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    is_walk_in: bool = False
    queue_number: Optional[int] = None
    follow_up_to: Optional[str] = None # ID of previous appointment
    prescription_id: Optional[str] = None # Link to digitized prescription

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    appointment_date: Optional[date] = None
    appointment_time: Optional[str] = None
    reason_for_visit: Optional[str] = None
    status: Optional[AppointmentStatus] = None
    queue_number: Optional[int] = None

class AppointmentInDB(AppointmentBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
