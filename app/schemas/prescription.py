from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

class PrescriptionStatus(str, Enum):
    PROCESSING = "processing"          # Currently in OCR/AI pipeline
    NEEDS_VERIFICATION = "needs_verification" # OCR done, needs human review
    VERIFIED = "verified"              # Staff has corrected/verified
    APPROVED = "approved"              # Doctor has approved (optional)
    REJECTED = "rejected"              # Unreadable or invalid

class ConfidenceStatus(str, Enum):
    HIGH = "high"       # > 90%
    MEDIUM = "medium"   # 70% - 90%
    LOW = "low"         # < 70%
    VERIFIED = "verified" # Human reviewed

class FieldConfidence(BaseModel):
    value: Any
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    status: ConfidenceStatus

    @classmethod
    def from_value(cls, val: Any, score: float):
        if score >= 90:
            status = ConfidenceStatus.HIGH
        elif score >= 70:
            status = ConfidenceStatus.MEDIUM
        else:
            status = ConfidenceStatus.LOW
        return cls(value=val, confidence_score=score, status=status)

class Medicine(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    medicine_name: Union[FieldConfidence, str] = Field(alias="name", default="")
    strength: Optional[Union[FieldConfidence, str]] = None
    dosage: Optional[Union[FieldConfidence, str]] = Field(alias="dose", default=None)
    frequency: Optional[Union[FieldConfidence, str]] = None
    duration: Optional[Union[FieldConfidence, str]] = None
    instructions: Optional[Union[FieldConfidence, str]] = None

class Diagnosis(BaseModel):
    condition: Union[FieldConfidence, str]
    abbreviation: Optional[str] = None
    notes: Optional[Union[FieldConfidence, str]] = None

class Investigation(BaseModel):
    test_name: Union[FieldConfidence, str]
    notes: Optional[Union[FieldConfidence, str]] = None

class PatientVitals(BaseModel):
    blood_pressure: Optional[Union[FieldConfidence, str]] = None
    temperature: Optional[Union[FieldConfidence, str]] = None
    pulse: Optional[Union[FieldConfidence, str]] = None
    weight: Optional[Union[FieldConfidence, str]] = None
    height: Optional[Union[FieldConfidence, str]] = None

class PrescriptionBase(BaseModel):
    appointment_id: Optional[str] = None
    patient_id: str
    doctor_id: str
    
    # Metadata extracted by OCR
    hospital_name: Optional[Union[FieldConfidence, str]] = None
    doctor_name: Optional[Union[FieldConfidence, str]] = None
    doctor_registration: Optional[Union[FieldConfidence, str]] = None
    prescription_date: Optional[Union[FieldConfidence, str]] = None
    patient_name: Optional[Union[FieldConfidence, str]] = None
    patient_age: Optional[Union[FieldConfidence, str]] = None
    patient_gender: Optional[Union[FieldConfidence, str]] = None
    
    # Clinical Data
    chief_complaint: Optional[Union[FieldConfidence, str]] = None
    clinical_notes: Optional[Union[FieldConfidence, str]] = None
    vitals: Optional[PatientVitals] = None
    diagnoses: List[Diagnosis] = []
    medicines: List[Medicine] = []
    investigations: List[Investigation] = []
    
    # Automations & Follow-up
    follow_up_date: Optional[Union[FieldConfidence, str]] = None
    special_notes: Optional[Union[FieldConfidence, str]] = None

class PrescriptionVersion(BaseModel):
    version: int
    data: dict  # The entire snapshot of PrescriptionBase at this version
    modified_by: str  # User ID or "AI_OCR"
    modified_at: datetime
    changes_made: Optional[str] = None

class PrescriptionCreate(PrescriptionBase):
    pass

class PrescriptionInDB(PrescriptionBase):
    id: str
    tenant_id: str
    status: Union[PrescriptionStatus, str] = PrescriptionStatus.PROCESSING
    ocr_provider: Optional[str] = None # e.g. "gemini-1.5-pro", "aws-textract"
    overall_confidence: Optional[float] = None
    image_url: Optional[str] = None
    original_text: Optional[str] = None # Raw OCR text dump
    
    versions: List[PrescriptionVersion] = []
    
    created_at: datetime
    updated_at: datetime
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
