"""
WhatsApp Flow Data-Exchange Handler
Handles all screen transitions for the clinic appointment flow:
  DOCTOR_SELECTION → DATE_TIME_SELECTION → SUMMARY → PAYMENT (complete)

Called by the /webhook/flow endpoint after decryption.
"""
import logging
import base64
import json
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from app.db.supabase import db
from app.db.retry import with_retry

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_doctors(tenant_id: str) -> List[Dict]:
    """Return all active doctors for the tenant."""
    try:
        res = with_retry(
            lambda: db.table("doctors")
            .select("id,name,specialization,consultation_fee")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .execute()
        )()
        return res.data or []
    except Exception as e:
        logger.error(f"[flow_handler] _get_doctors error: {e}")
        return []


def _get_specialties(doctors: List[Dict]) -> List[Dict]:
    """Build a deduplicated list of specialties from the doctors list."""
    seen = {}
    for d in doctors:
        spec = d.get("specialization", "General")
        if spec and spec not in seen:
            seen[spec] = {"id": spec, "title": spec}
    return list(seen.values())


def _get_doctors_for_specialty(doctors: List[Dict], specialty: str) -> List[Dict]:
    """Filter doctors by specialty."""
    return [
        {"id": d["id"], "title": f"Dr. {d['name']} (₹{d.get('consultation_fee', 0)})"}
        for d in doctors
        if d.get("specialization") == specialty
    ]


def _get_available_dates(doctor_id: str, tenant_id: str, days_ahead: int = 14) -> List[Dict]:
    """Return the next `days_ahead` days that the doctor has a schedule."""
    try:
        # Get the doctor's weekly schedule (day_of_week: 0=Mon … 6=Sun)
        res = with_retry(
            lambda: db.table("doctor_schedules")
            .select("day_of_week")
            .eq("doctor_id", doctor_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )()
        work_days = {r["day_of_week"] for r in (res.data or [])}
    except Exception:
        # Fallback: offer weekdays
        work_days = {0, 1, 2, 3, 4}

    today = date.today()
    dates = []
    # Start from 0 to include today
    for i in range(0, days_ahead):
        d = today + timedelta(days=i)
        # Python weekday(): 0=Mon … 6=Sun
        if d.weekday() in work_days or not work_days:
            dates.append({"id": d.isoformat(), "title": d.strftime("%a, %d %b %Y")})
        if len(dates) >= 7:
            break
    return dates


def _get_available_slots(doctor_id: str, tenant_id: str, date_str: str) -> List[Dict]:
    """Return available time slots for a doctor on a given date."""
    try:
        target = date.fromisoformat(date_str)
        day_of_week = target.weekday()

        # Get schedule for that day
        sched_res = with_retry(
            lambda: db.table("doctor_schedules")
            .select("start_time,end_time,slot_duration_minutes,break_start,break_end")
            .eq("doctor_id", doctor_id)
            .eq("tenant_id", tenant_id)
            .eq("day_of_week", day_of_week)
            .execute()
        )()

        if not sched_res.data:
            return []

        sched = sched_res.data[0]

        # Get already-booked slots
        booked_res = with_retry(
            lambda: db.table("appointments")
            .select("appointment_time")
            .eq("doctor_id", doctor_id)
            .eq("tenant_id", tenant_id)
            .eq("appointment_date", date_str)
            .in_("status", ["scheduled", "confirmed", "waiting", "checked-in", "in consultation", "completed"])
            .execute()
        )()
        booked_times = {r["appointment_time"][:5] for r in (booked_res.data or [])}

        # Generate slots
        from datetime import datetime, time as dtime
        slot_dur = sched.get("slot_duration_minutes", 30)
        start = datetime.strptime(sched["start_time"][:5], "%H:%M")
        end   = datetime.strptime(sched["end_time"][:5],   "%H:%M")

        break_start = break_end = None
        if sched.get("break_start") and sched.get("break_end"):
            break_start = datetime.strptime(sched["break_start"][:5], "%H:%M")
            break_end   = datetime.strptime(sched["break_end"][:5],   "%H:%M")

        slots = []
        cur = start
        while cur < end:
            time_str = cur.strftime("%H:%M")
            # Skip break
            in_break = break_start and break_end and break_start <= cur < break_end
            
            is_past = False
            if date_str == datetime.now().strftime("%Y-%m-%d"):
                if cur.time() <= datetime.now().time():
                    is_past = True
                    
            if not in_break and not is_past and time_str not in booked_times:
                slots.append({"id": time_str, "title": cur.strftime("%I:%M %p")})
            from datetime import timedelta as td
            cur += td(minutes=slot_dur)
        return slots[:20]  # cap at 20

    except Exception as e:
        logger.error(f"[flow_handler] _get_available_slots error: {e}")
        return [
            {"id": "09:00", "title": "09:00 AM"},
            {"id": "10:00", "title": "10:00 AM"},
            {"id": "11:00", "title": "11:00 AM"},
        ]


def _decode_flow_token(flow_token: str) -> Dict:
    """Decode the state embedded in the flow_token (format: tk_<base64url>)."""
    try:
        if flow_token.startswith("tk_"):
            b64 = flow_token[3:]
            padding = "=" * ((-len(b64)) % 4)
            return json.loads(base64.urlsafe_b64decode(b64 + padding).decode())
    except Exception:
        pass
    return {}


# ─── Main handler ──────────────────────────────────────────────────────────────

def handle_flow_data_exchange(decrypted_body: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
    """
    Process a WhatsApp Flow data_exchange payload and return the response data dict.
    The caller is responsible for encrypting the returned dict.

    Returns a dict with keys `screen` and `data` (following Meta's flow response spec).
    """
    action   = decrypted_body.get("action", "")
    screen   = decrypted_body.get("screen", "")
    payload  = decrypted_body.get("data", {})
    flow_token = decrypted_body.get("flow_token", "")
    trigger  = payload.get("trigger", "")
    version  = decrypted_body.get("version", "3.0")

    state = _decode_flow_token(flow_token)
    patient_name  = state.get("n", "")
    patient_phone = state.get("p", "")

    logger.info(f"[flow_handler] screen={screen} trigger={trigger} action={action}")

    doctors = _get_doctors(tenant_id)

    # ── INITIAL SCREEN: open → DOCTOR_SELECTION ───────────────────────────────
    if action in ("INIT", "init") or (not trigger and screen in ("", "DOCTOR_SELECTION", None)):
        specialties = _get_specialties(doctors)
        return {
            "version": version,
            "screen": "DOCTOR_SELECTION",
            "data": {
                "specialties": specialties,
                "doctors": [],
                "is_doctor_enabled": False,
                "patient_name_prefill": patient_name,
                "patient_phone_prefill": patient_phone,
            }
        }

    # ── DOCTOR_SELECTION: specialty chosen → load doctors ─────────────────────
    if trigger == "specialty_selected":
        specialty = payload.get("specialty", "")
        matching_doctors = _get_doctors_for_specialty(doctors, specialty)
        return {
            "version": version,
            "screen": "DOCTOR_SELECTION",
            "data": {
                "specialties": _get_specialties(doctors),
                "doctors": matching_doctors,
                "is_doctor_enabled": bool(matching_doctors),
                "patient_name_prefill": patient_name,
                "patient_phone_prefill": patient_phone,
            }
        }

    # ── DOCTOR_SELECTION: Next clicked → load DATE_TIME_SELECTION ─────────────
    if trigger == "doctor_selected_continue":
        doctor_id = payload.get("doctor", "")
        specialty  = payload.get("specialty", "")
        dates = _get_available_dates(doctor_id, tenant_id)
        return {
            "version": version,
            "screen": "DATE_TIME_SELECTION",
            "data": {
                "dates": dates,
                "times": [],
                "is_time_enabled": False,
                "specialty": specialty,
                "doctor": doctor_id,
                "patient_name_prefill": patient_name,
                "patient_phone_prefill": patient_phone,
            }
        }

    # ── DATE_TIME_SELECTION: date chosen → load time slots ────────────────────
    if trigger == "date_selected":
        doctor_id = payload.get("doctor", "")
        specialty  = payload.get("specialty", "")
        date_str   = payload.get("date", "")
        slots = _get_available_slots(doctor_id, tenant_id, date_str)
        return {
            "version": version,
            "screen": "DATE_TIME_SELECTION",
            "data": {
                "dates": _get_available_dates(doctor_id, tenant_id),
                "times": slots,
                "is_time_enabled": bool(slots),
                "specialty": specialty,
                "doctor": doctor_id,
                "patient_name_prefill": patient_name,
                "patient_phone_prefill": patient_phone,
            }
        }

    # ── DATE_TIME_SELECTION: Continue → SUMMARY ───────────────────────────────
    if trigger == "appointment_summary":
        doctor_id  = payload.get("doctor", "")
        specialty  = payload.get("specialty", "")
        date_str   = payload.get("date", "")
        time_str   = payload.get("time", "")
        name       = payload.get("name", patient_name)
        phone      = payload.get("phone", patient_phone)

        # Resolve doctor name
        doctor_name = "Doctor"
        for d in doctors:
            if d["id"] == doctor_id:
                doctor_name = f"Dr. {d['name']}"
                break

        summary_text = (
            f"📋 *Appointment Summary*\n\n"
            f"👤 Patient: {name}\n"
            f"🏥 Specialty: {specialty}\n"
            f"👨‍⚕️ Doctor: {doctor_name}\n"
            f"📅 Date: {date_str}\n"
            f"⏰ Time: {time_str}"
        )
        return {
            "version": version,
            "screen": "SUMMARY",
            "data": {
                "summary_text": summary_text,
                "specialty": specialty,
                "doctor": doctor_id,
                "doctor_name": doctor_name,
                "date": date_str,
                "time": time_str,
                "patient_name_prefill": name,
                "patient_phone_prefill": phone,
            }
        }

    # ── SUMMARY: Proceed to Payment → PAYMENT ─────────────────────────────────
    if trigger == "proceed_to_payment":
        return {
            "version": version,
            "screen": "PAYMENT",
            "data": {
                "specialty": payload.get("specialty", ""),
                "doctor": payload.get("doctor", ""),
                "date": payload.get("date", ""),
                "time": payload.get("time", ""),
                "name": payload.get("name", patient_name),
                "phone": payload.get("phone", patient_phone),
                "email": payload.get("email", ""),
                "symptoms": payload.get("symptoms", "")
            }
        }

    # ── PAYMENT: Confirm → complete flow (terminal) ───────────────────────────
    if trigger in ("confirm_appointment", "payment_done", "confirm_and_pay", "final_confirm") or screen == "PAYMENT":
        doctor_id = payload.get("doctor", "")
        date_val = payload.get("date", "")
        time_val = payload.get("time", "")
        symptoms_val = payload.get("symptoms", "")

        # Return terminal complete signal — patient_agent will receive the
        # nfm_reply in the next webhook message and book the appointment
        return {
            "version": version,
            "screen": "SUCCESS",
            "data": {
                "extension_message_response": {
                    "params": {
                        "flow_token": flow_token,
                        "status": "appointment_confirmed",
                        "doctor": doctor_id,
                        "date": date_val,
                        "time": time_val,
                        "symptoms": symptoms_val
                    }
                }
            }
        }

    # ── Fallback: re-send DOCTOR_SELECTION ────────────────────────────────────
    logger.warning(f"[flow_handler] Unhandled trigger={trigger!r} screen={screen!r} — falling back to DOCTOR_SELECTION")
    specialties = _get_specialties(doctors)
    return {
        "version": version,
        "screen": "DOCTOR_SELECTION",
        "data": {
            "specialties": specialties,
            "doctors": [],
            "is_doctor_enabled": False,
            "patient_name_prefill": patient_name,
            "patient_phone_prefill": patient_phone,
        }
    }
