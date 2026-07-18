from fastapi import APIRouter
from app.api.v1.endpoints import tenants, whatsapp, patients, doctors, appointments, ai, ipd, laboratory, users, schedules, webhooks, prescriptions, reports

api_router = APIRouter()
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["whatsapp"])
api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(doctors.router, prefix="/doctors", tags=["doctors"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(ipd.router, prefix="/ipd", tags=["ipd"])
api_router.include_router(laboratory.router, prefix="/laboratory", tags=["laboratory"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(prescriptions.router, prefix="/prescriptions", tags=["prescriptions"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
from app.api.v1.endpoints import debug_scheduler
api_router.include_router(debug_scheduler.router, prefix="/debug", tags=["debug"])
