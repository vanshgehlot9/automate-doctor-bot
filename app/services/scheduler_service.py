import asyncio
import json
import os
import logging
from datetime import datetime, timedelta, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db.supabase import db
from app.services.whatsapp.sender import WhatsAppSender
from app.services.patient_service import PatientService
from app.services.prescription_service import PrescriptionService

logger = logging.getLogger(__name__)

STATE_FILE = "scheduler_state.json"

class ReminderScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        from app.core.config import settings
        self.sender = WhatsAppSender(settings.WHATSAPP_TOKEN, settings.WHATSAPP_PHONE_NUMBER_ID)
        self.sent_records = self._load_state()

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    return set(json.load(f))
            except:
                pass
        return set()

    def _save_state(self):
        with open(STATE_FILE, "w") as f:
            json.dump(list(self.sent_records), f)

    def _has_been_sent(self, key: str) -> bool:
        return key in self.sent_records

    def _mark_as_sent(self, key: str):
        self.sent_records.add(key)
        self._save_state()

    async def _get_all_tenants(self):
        if not db: return []
        res = db.table("tenants").select("id").execute()
        return [row["id"] for row in res.data] if res.data else []

    async def check_appointments(self):
        logger.info("[Scheduler] Checking for upcoming appointments...")
        if not db: return
        
        now = datetime.now()
        target_time = now + timedelta(hours=2)
        target_date_str = target_time.strftime("%Y-%m-%d")
        
        res = db.table("appointments").select("*, patients(name, phone_number), doctors(name)").eq("appointment_date", target_date_str).eq("status", "scheduled").execute()
        if not res.data: return
            
        for appt in res.data:
            appt_time_str = appt.get("appointment_time")
            if not appt_time_str: continue
            
            try:
                appt_dt = datetime.strptime(f"{target_date_str} {appt_time_str}", "%Y-%m-%d %H:%M:%S")
            except:
                try:
                    appt_dt = datetime.strptime(f"{target_date_str} {appt_time_str}", "%Y-%m-%d %H:%M")
                except:
                    continue
            
            diff = (appt_dt - now).total_seconds() / 3600
            if 1.75 <= diff <= 2.25:
                rem_key = f"appt_rem_{appt['id']}"
                if not self._has_been_sent(rem_key):
                    pat = appt.get("patients", {})
                    doc = appt.get("doctors", {})
                    phone = pat.get("phone_number")
                    
                    if phone:
                        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
                        msg = (
                            f"⏰ *Friendly Reminder*\n\n"
                            f"Hi {pat.get('name', 'there')}, your appointment with Dr. {doc.get('name', 'Doctor')} "
                            f"is coming up in about 2 hours at *{appt_time_str}*.\n\n"
                            f"Please arrive 10 minutes early. Type *menu* if you need to reschedule or view details."
                        )
                        success = self.sender.send_message(clean_phone, msg)
                        if success:
                            logger.info(f"Sent 2h reminder to {clean_phone} for appointment {appt['id']}")
                            self._mark_as_sent(rem_key)


    async def check_medicines_morning(self):
        await self._send_medicine_reminders("Morning (8:00 AM)", "🌅 Good morning! It's time to take your morning medicines.")

    async def check_medicines_afternoon(self):
        await self._send_medicine_reminders("Afternoon (1:00 PM)", "☀️ Good afternoon! Just a quick reminder for your afternoon medicines.")

    async def check_medicines_night(self):
        await self._send_medicine_reminders("Night (9:00 PM)", "🌙 Good evening! Don't forget to take your night-time medicines.")

    async def _send_medicine_reminders(self, schedule_key: str, greeting: str):
        logger.info(f"[Scheduler] Sending {schedule_key} medicine reminders...")
        tenants = await self._get_all_tenants()
        for tenant_id in tenants:
            patients = PatientService.get_all_patients(tenant_id)
            for p in patients:
                if not p.mobile_number: continue
                sched = PrescriptionService.get_medicine_schedule(tenant_id, p.id)
                meds = sched.get(schedule_key, [])
                if meds:
                    today_str = date.today().isoformat()
                    rem_key = f"med_rem_{p.id}_{schedule_key}_{today_str}"
                    if not self._has_been_sent(rem_key):
                        clean_phone = p.mobile_number.replace("+", "").replace(" ", "").replace("-", "")
                        med_list = "\n".join([f"• {m}" for m in meds])
                        msg = f"{greeting}\n\n*Your Medicines:*\n{med_list}\n\n_Reply with 'menu' to view your full prescription details._"
                        
                        success = self.sender.send_message(clean_phone, msg)
                        if success:
                            self._mark_as_sent(rem_key)

    async def send_mood_checkins(self):
        logger.info("[Scheduler] Sending mood check-ins...")
        tenants = await self._get_all_tenants()
        today_str = date.today().isoformat()
        
        for tenant_id in tenants:
            patients = PatientService.get_all_patients(tenant_id)
            for p in patients:
                if not p.mobile_number: continue
                
                rem_key = f"mood_checkin_{p.id}_{today_str}"
                if not self._has_been_sent(rem_key):
                    clean_phone = p.mobile_number.replace("+", "").replace(" ", "").replace("-", "")
                    
                    payload = {
                        "type": "interactive",
                        "interactive": {
                            "type": "button",
                            "body": {
                                "text": f"Hi {p.name}! Just a quick daily check-in from Aatomate Health. 🧠 How is your mood today?"
                            },
                            "action": {
                                "buttons": [
                                    {"type": "reply", "reply": {"id": "chk_great", "title": "Great! 😊"}},
                                    {"type": "reply", "reply": {"id": "chk_okay", "title": "Doing Okay 😐"}},
                                    {"type": "reply", "reply": {"id": "chk_bad", "title": "Not so good 🤒"}}
                                ]
                            }
                        }
                    }
                    success = self.sender.send_interactive_message(clean_phone, payload)
                    if success:
                        self._mark_as_sent(rem_key)

    async def send_water_reminders(self):
        logger.info("[Scheduler] Sending water reminders...")
        tenants = await self._get_all_tenants()
        
        # We track water reminders by the hour/minute block so it doesn't duplicate in the same 30 min window
        now = datetime.now()
        time_block = now.strftime("%Y-%m-%d_%H") + ("_30" if now.minute >= 30 else "_00")
        
        for tenant_id in tenants:
            patients = PatientService.get_all_patients(tenant_id)
            for p in patients:
                if not p.mobile_number: continue
                
                rem_key = f"water_rem_{p.id}_{time_block}"
                if not self._has_been_sent(rem_key):
                    clean_phone = p.mobile_number.replace("+", "").replace(" ", "").replace("-", "")
                    
                    payload = {
                        "type": "interactive",
                        "interactive": {
                            "type": "button",
                            "body": {
                                "text": f"💧 Water Reminder for {p.name}!\n\nIt's time to drink a glass of water to stay hydrated!"
                            },
                            "action": {
                                "buttons": [
                                    {"type": "reply", "reply": {"id": "water_drank", "title": "I drank it! 💧"}}
                                ]
                            }
                        }
                    }
                    success = self.sender.send_interactive_message(clean_phone, payload)
                    if success:
                        self._mark_as_sent(rem_key)

    def start(self):
        self.scheduler.add_job(self.check_appointments, 'interval', minutes=15)
        self.scheduler.add_job(self.check_medicines_morning, 'cron', hour=8, minute=0)
        self.scheduler.add_job(self.check_medicines_afternoon, 'cron', hour=13, minute=0)
        self.scheduler.add_job(self.check_medicines_night, 'cron', hour=21, minute=0)
        self.scheduler.add_job(self.send_mood_checkins, 'cron', hour=16, minute=0)
        self.scheduler.add_job(self.send_water_reminders, 'interval', minutes=30)
        self.scheduler.start()
        logger.info("[Scheduler] Native Background Scheduler started successfully.")

    def stop(self):
        self.scheduler.shutdown()
        logger.info("[Scheduler] Native Background Scheduler stopped.")

scheduler_service = ReminderScheduler()
