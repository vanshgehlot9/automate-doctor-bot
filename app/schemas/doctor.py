from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class DoctorBase(BaseModel):
    name: str
    specialization: str
    qualifications: List[str]
    experience_years: int
    languages: List[str]
    consultation_fee: float
    availability_schedule: Dict # E.g., {"monday": ["09:00-13:00", "15:00-18:00"]}
    is_active: bool = True
    whatsapp_number: Optional[str] = None  # e.g. "919876543210" — used to identify doctor in bot

class DoctorCreate(DoctorBase):
    pass

class DoctorUpdate(BaseModel):
    name: Optional[str] = None
    specialization: Optional[str] = None
    qualifications: Optional[List[str]] = None
    experience_years: Optional[int] = None
    languages: Optional[List[str]] = None
    consultation_fee: Optional[float] = None
    availability_schedule: Optional[Dict] = None
    is_active: Optional[bool] = None
    whatsapp_number: Optional[str] = None  # Allow updating WhatsApp number

class DoctorInDB(DoctorBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
