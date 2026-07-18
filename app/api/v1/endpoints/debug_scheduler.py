from fastapi import APIRouter
from app.services.scheduler_service import scheduler_service

router = APIRouter()

@router.get("/trigger-appointments")
async def trigger_appointments():
    await scheduler_service.check_appointments()
    return {"status": "triggered appointment checks"}

@router.get("/trigger-medicines")
async def trigger_medicines():
    await scheduler_service.check_medicines_morning()
    return {"status": "triggered morning medicine checks"}

@router.get("/trigger-health")
async def trigger_health():
    await scheduler_service.send_mood_checkins()
    return {"status": "triggered mood checkins"}

@router.get("/trigger-water")
async def trigger_water():
    await scheduler_service.send_water_reminders()
    return {"status": "triggered water reminders"}
