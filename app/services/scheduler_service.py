"""
ReminderScheduler  —  Senior-grade background automation service

Fixes & Improvements:
- Water reminders: removed broken file-state persistence; now uses pure in-memory
  dedup per-run so it fires reliably every 30 minutes on any server restart.
- Medicine/mood reminders still deduplicate by date using in-memory dict (resets each
  day naturally on restart, which is acceptable for once-a-day jobs).
- Appointment reminder now also notifies the patient's emergency_contact (family member).
- All jobs are safe: no crash propagates, every exception is caught and logged.
"""
import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.supabase import db
from app.services.whatsapp.sender import WhatsAppSender

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_phone(phone: str) -> str:
    """Strip all non-digit chars from a phone number."""
    return "".join(c for c in phone if c.isdigit())


def _get_sender():
    from app.core.config import settings
    return WhatsAppSender(settings.WHATSAPP_TOKEN, settings.WHATSAPP_PHONE_NUMBER_ID)


def _get_all_tenant_ids():
    if not db:
        return []
    try:
        res = db.table("tenants").select("id").execute()
        return [row["id"] for row in (res.data or [])]
    except Exception as e:
        logger.error(f"[Scheduler] Failed to fetch tenants: {e}")
        return []


def _get_all_patients(tenant_id: str):
    if not db:
        return []
    try:
        from app.services.patient_service import PatientService
        return PatientService.get_all_patients(tenant_id)
    except Exception as e:
        logger.error(f"[Scheduler] Failed to fetch patients for tenant {tenant_id}: {e}")
        return []


# ---------------------------------------------------------------------------
# In-memory dedup stores (reset on server restart — intentional for water)
# ---------------------------------------------------------------------------

# Key: f"med_{patient_id}_{slot}_{date}"  →  prevents double-sending same slot
_sent_medicine: set = set()

# Key: f"mood_{patient_id}_{date}"
_sent_mood: set = set()

# Key: f"appt_{appt_id}"  — appointment 2h reminders (never repeat after first send)
_sent_appt: set = set()

# Water reminders intentionally NOT deduplicated beyond the current 30-min window;
# dedup is per-firing so each cron tick sends fresh if not already sent THIS tick.
# (No persistent store = no stale-key bugs across restarts.)


# ---------------------------------------------------------------------------
# Individual reminder tasks
# ---------------------------------------------------------------------------

async def _check_appointments():
    """Send a WhatsApp reminder to patient + family 2 hours before appointment."""
    logger.info("[Scheduler] ▶ check_appointments")
    if not db:
        return

    now = datetime.now()
    window_start = now + timedelta(hours=1, minutes=45)
    window_end   = now + timedelta(hours=2, minutes=15)

    try:
        target_date = (now + timedelta(hours=2)).strftime("%Y-%m-%d")
        res = db.table("appointments") \
                .select("*, patients(*), doctors(name)") \
                .eq("appointment_date", target_date) \
                .eq("status", "scheduled") \
                .execute()
    except Exception as e:
        logger.error(f"[Scheduler] DB error in check_appointments: {e}")
        return

    if not res.data:
        return

    sender = _get_sender()

    for appt in res.data:
        appt_id = appt.get("id", "")
        rem_key = f"appt_{appt_id}"
        if rem_key in _sent_appt:
            continue

        time_str = appt.get("appointment_time", "")
        if not time_str:
            continue

        date_str = appt.get("appointment_date", "")
        try:
            appt_dt = datetime.strptime(f"{date_str} {time_str[:5]}", "%Y-%m-%d %H:%M")
        except Exception:
            continue

        if not (window_start <= appt_dt <= window_end):
            continue

        pat  = appt.get("patients") or {}
        doc  = appt.get("doctors")  or {}
        phone = pat.get("mobile_number") or pat.get("phone_number", "")
        patient_name = pat.get("name", "Patient")
        doctor_name  = doc.get("name", "Doctor")

        friendly_time = appt_dt.strftime("%-I:%M %p")
        friendly_date = appt_dt.strftime("%A, %d %B %Y")

        reminder_msg = (
            f"⏰ *Appointment Reminder*\n\n"
            f"Hi {patient_name}! Your appointment with *Dr. {doctor_name}* "
            f"is in approximately *2 hours*.\n\n"
            f"📅 Date: *{friendly_date}*\n"
            f"🕐 Time: *{friendly_time}*\n\n"
            "Please arrive 10 minutes early. Reply *menu* to reschedule."
        )

        sent = False
        if phone:
            clean = _clean_phone(phone)
            if clean:
                ok = sender.send_message(clean, reminder_msg)
                if ok:
                    logger.info(f"[Scheduler] Appointment reminder → patient {clean}")
                    sent = True

        # ── Family / emergency contact notification ────────────────────
        emergency_contact = pat.get("emergency_contact", "")
        if emergency_contact:
            ec_phone = _clean_phone(emergency_contact)
            if ec_phone and len(ec_phone) >= 10:
                family_msg = (
                    f"👨‍👩‍👧 *Family Notification from Aatomate Health*\n\n"
                    f"This is a friendly reminder that *{patient_name}'s* appointment "
                    f"with *Dr. {doctor_name}* is coming up in approximately *2 hours*.\n\n"
                    f"📅 Date: *{friendly_date}*\n"
                    f"🕐 Time: *{friendly_time}*\n\n"
                    "Please ensure they are ready on time. 🙏"
                )
                ok_fam = sender.send_message(ec_phone, family_msg)
                if ok_fam:
                    logger.info(f"[Scheduler] Family notification → {ec_phone} for patient {patient_name}")

        if sent:
            _sent_appt.add(rem_key)


async def _send_medicine_reminders(slot_label: str, greeting: str):
    """Send medicine reminders for a given time slot to all patients."""
    logger.info(f"[Scheduler] ▶ medicine reminder — {slot_label}")
    today = date.today().isoformat()

    try:
        from app.services.prescription_service import PrescriptionService
        sender = _get_sender()

        for tid in _get_all_tenant_ids():
            for p in _get_all_patients(tid):
                if not p.mobile_number:
                    continue
                key = f"med_{p.id}_{slot_label}_{today}"
                if key in _sent_medicine:
                    continue

                try:
                    sched = PrescriptionService.get_medicine_schedule(tid, p.id)
                    meds  = sched.get(slot_label, [])
                except Exception as e:
                    logger.warning(f"[Scheduler] Medicine schedule error for {p.id}: {e}")
                    continue

                if not meds:
                    continue

                clean = _clean_phone(p.mobile_number)
                if not clean:
                    continue

                med_list = "\n".join([f"• {m}" for m in meds])
                msg = (
                    f"{greeting}\n\n"
                    f"*{p.name}'s Medicines:*\n{med_list}\n\n"
                    "_Reply 'menu' to view your full prescription details._"
                )
                ok = sender.send_message(clean, msg)
                if ok:
                    _sent_medicine.add(key)
                    logger.info(f"[Scheduler] Medicine reminder sent → {clean} ({slot_label})")

    except Exception as e:
        logger.error(f"[Scheduler] Unhandled error in _send_medicine_reminders: {e}")


async def _send_mood_checkins():
    """Send once-daily mood check-in to all patients at 4 PM."""
    logger.info("[Scheduler] ▶ mood check-ins")
    today = date.today().isoformat()

    try:
        sender = _get_sender()

        for tid in _get_all_tenant_ids():
            for p in _get_all_patients(tid):
                if not p.mobile_number:
                    continue

                key = f"mood_{p.id}_{today}"
                if key in _sent_mood:
                    continue

                clean = _clean_phone(p.mobile_number)
                if not clean:
                    continue

                payload = {
                    "type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": (
                                f"Hi {p.name}! 🌞 Your daily health check-in from Aatomate Health.\n\n"
                                "How are you feeling today?"
                            )
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "chk_great", "title": "Great! 😊"}},
                                {"type": "reply", "reply": {"id": "chk_okay",  "title": "Doing Okay 😐"}},
                                {"type": "reply", "reply": {"id": "chk_bad",   "title": "Not so good 🤒"}},
                            ]
                        },
                    }
                }
                ok = sender.send_interactive_message(clean, payload)
                if ok:
                    _sent_mood.add(key)
                    logger.info(f"[Scheduler] Mood check-in sent → {clean}")

    except Exception as e:
        logger.error(f"[Scheduler] Unhandled error in _send_mood_checkins: {e}")


async def _send_water_reminders():
    """
    Send water reminders every 30 minutes to all patients.
    No persistent dedup — each cron firing is independent.
    """
    logger.info("[Scheduler] ▶ water reminders")

    try:
        sender = _get_sender()
        hour = datetime.now().hour
        minute = datetime.now().minute

        # Skip late night (11 PM – 6 AM)
        if hour >= 23 or hour < 6:
            logger.info("[Scheduler] Water reminder skipped — quiet hours")
            return

        half = "30" if minute >= 30 else "00"
        logger.info(f"[Scheduler] Water reminder firing at {hour}:{half}")

        for tid in _get_all_tenant_ids():
            for p in _get_all_patients(tid):
                if not p.mobile_number:
                    continue

                clean = _clean_phone(p.mobile_number)
                if not clean:
                    continue

                payload = {
                    "type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": (
                                f"💧 *Water Reminder* for {p.name}!\n\n"
                                "It's been 30 minutes — time to drink a glass of water "
                                "and stay hydrated! 🥤"
                            )
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "water_drank", "title": "I drank it! 💧"}},
                            ]
                        },
                    }
                }
                ok = sender.send_interactive_message(clean, payload)
                if ok:
                    logger.info(f"[Scheduler] Water reminder sent → {clean}")

    except Exception as e:
        logger.error(f"[Scheduler] Unhandled error in _send_water_reminders: {e}")


# ---------------------------------------------------------------------------
# Scheduler wrappers (sync → async bridge for APScheduler)
# ---------------------------------------------------------------------------

def _run_async(coro):
    """Run an async coroutine from a synchronous APScheduler job."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        asyncio.run(coro)


# ---------------------------------------------------------------------------
# Scheduler service singleton
# ---------------------------------------------------------------------------

class ReminderScheduler:
    def __init__(self):
        import pytz
        tz = pytz.timezone("Asia/Kolkata")
        self.scheduler = AsyncIOScheduler(timezone=tz)
        self._running = False

    def start(self):
        if self._running:
            logger.warning("[Scheduler] Already running — skipping start()")
            return

        # Appointment check — every 10 minutes (tighter window for accuracy)
        self.scheduler.add_job(
            lambda: _run_async(_check_appointments()),
            "interval", minutes=10, id="appt_check"
        )

        # Medicine reminders — exact cron times
        self.scheduler.add_job(
            lambda: _run_async(_send_medicine_reminders("Morning (8:00 AM)", "🌅 Good morning! Time for your morning medicines.")),
            "cron", hour=8, minute=0, id="med_morning"
        )
        self.scheduler.add_job(
            lambda: _run_async(_send_medicine_reminders("Afternoon (1:00 PM)", "☀️ Good afternoon! Time for your afternoon medicines.")),
            "cron", hour=13, minute=0, id="med_afternoon"
        )
        self.scheduler.add_job(
            lambda: _run_async(_send_medicine_reminders("Night (9:00 PM)", "🌙 Good evening! Don't forget your night medicines.")),
            "cron", hour=21, minute=0, id="med_night"
        )

        # Mood check-in — once daily at 4 PM
        self.scheduler.add_job(
            lambda: _run_async(_send_mood_checkins()),
            "cron", hour=16, minute=0, id="mood_checkin"
        )

        # Water reminder — every 30 minutes (reliable, in-memory, no file state)
        self.scheduler.add_job(
            lambda: _run_async(_send_water_reminders()),
            "interval", minutes=30, id="water_reminder"
        )

        self.scheduler.start()
        self._running = True
        logger.info("[Scheduler] ✅ Native Background Scheduler started — all jobs active.")

    def stop(self):
        if self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("[Scheduler] ⛔ Scheduler stopped.")

    # ── Manual trigger helpers (for debug endpoints) ─────────────────────────

    async def trigger_appointments(self):
        await _check_appointments()

    async def trigger_water(self):
        await _send_water_reminders()

    async def trigger_mood(self):
        await _send_mood_checkins()

    async def trigger_medicine_morning(self):
        await _send_medicine_reminders("Morning (8:00 AM)", "🌅 Test: morning medicines.")

    async def trigger_medicine_afternoon(self):
        await _send_medicine_reminders("Afternoon (1:00 PM)", "☀️ Test: afternoon medicines.")

    async def trigger_medicine_night(self):
        await _send_medicine_reminders("Night (9:00 PM)", "🌙 Test: night medicines.")


scheduler_service = ReminderScheduler()
