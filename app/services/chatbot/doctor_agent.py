import logging
import uuid
from typing import Dict, Any, Optional
from datetime import date, datetime
from app.services.whatsapp.sender import WhatsAppSender
from app.schemas.whatsapp_account import WhatsAppAccount
from app.services.doctor_service import DoctorService
from app.db.supabase import db
from app.db.retry import with_retry

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# In-memory session store  {phone_number: state}
# ─────────────────────────────────────────────
_sessions: Dict[str, Dict] = {}

def _get_session(phone: str) -> Dict:
    if phone not in _sessions:
        _sessions[phone] = {}
    return _sessions[phone]

def _clear_session(phone: str):
    _sessions[phone] = {}

# ─────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────

def _get_today_appointments(tenant_id: str, doctor_id: str):
    today = date.today().isoformat()
    try:
        res = with_retry(lambda: db.table("appointments")
            .select("*, patients(id,name,mobile_number,dob,blood_group,gender,allergies,chronic_diseases)")
            .eq("tenant_id", tenant_id)
            .eq("doctor_id", doctor_id)
            .eq("appointment_date", today)
            .order("appointment_time")
            .execute())()
            
        appts = res.data or []
        for appt in appts:
            patient_id = appt.get("patient_id")
            if patient_id:
                # Check if patient has any past completed or checked-in appointments
                past = with_retry(lambda: db.table("appointments")
                    .select("id")
                    .eq("patient_id", patient_id)
                    .in_("status", ["completed", "checked-in"])
                    .lt("appointment_date", today)
                    .limit(1)
                    .execute())()
                appt["is_returning"] = bool(past.data)
            else:
                appt["is_returning"] = False
                
        return appts
    except Exception as e:
        logger.error(f"[DoctorAgent] get_today_appointments error: {e}")
        return []

def _search_patients(tenant_id: str, query: str):
    """Search patients by name (ilike) or mobile number."""
    try:
        by_name = with_retry(lambda: db.table("patients")
            .select("id,name,mobile_number,dob,blood_group,gender")
            .eq("tenant_id", tenant_id)
            .ilike("name", f"%{query}%")
            .limit(10)
            .execute())()
        by_mobile = with_retry(lambda: db.table("patients")
            .select("id,name,mobile_number,dob,blood_group,gender")
            .eq("tenant_id", tenant_id)
            .ilike("mobile_number", f"%{query}%")
            .limit(10)
            .execute())()
        seen = {}
        for row in (by_name.data or []) + (by_mobile.data or []):
            seen[row["id"]] = row
        return list(seen.values())[:10]
    except Exception as e:
        logger.error(f"[DoctorAgent] search_patients error: {e}")
        return []

def _get_patient(patient_id: str):
    try:
        res = with_retry(lambda: db.table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute())()
        return res.data
    except Exception as e:
        logger.error(f"[DoctorAgent] get_patient error: {e}")
        return None

def _get_lab_tests(tenant_id: str, patient_id: str, limit=5):
    try:
        res = with_retry(lambda: db.table("lab_tests")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("patient_id", patient_id)
            .order("test_date", desc=True)
            .limit(limit)
            .execute())()
        return res.data or []
    except Exception as e:
        logger.error(f"[DoctorAgent] get_lab_tests error: {e}")
        return []

def _get_prescriptions(tenant_id: str, patient_id: str, limit=3):
    try:
        res = with_retry(lambda: db.table("prescriptions")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("patient_id", patient_id)
            .order("prescription_date", desc=True)
            .limit(limit)
            .execute())()
        return res.data or []
    except Exception as e:
        logger.error(f"[DoctorAgent] get_prescriptions error: {e}")
        return []

def _get_reports(tenant_id: str, patient_id: str, limit=5):
    try:
        res = with_retry(lambda: db.table("medical_reports")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("patient_id", patient_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute())()
        return res.data or []
    except Exception as e:
        logger.error(f"[DoctorAgent] get_reports error: {e}")
        return []

def _get_patient_appointment_today(tenant_id: str, doctor_id: str, patient_id: str):
    today = date.today().isoformat()
    try:
        res = with_retry(lambda: db.table("appointments")
            .select("id,status")
            .eq("tenant_id", tenant_id)
            .eq("doctor_id", doctor_id)
            .eq("patient_id", patient_id)
            .eq("appointment_date", today)
            .limit(1)
            .execute())()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"[DoctorAgent] get_patient_appointment error: {e}")
        return None

def _update_appointment_status(tenant_id: str, appointment_id: str, status: str):
    try:
        with_retry(lambda: db.table("appointments")
            .update({"status": status, "updated_at": datetime.utcnow().isoformat()})
            .eq("tenant_id", tenant_id)
            .eq("id", appointment_id)
            .execute())()
        return True
    except Exception as e:
        logger.error(f"[DoctorAgent] update_appointment_status error: {e}")
        return False

def _save_prescription(tenant_id: str, doctor_id: str, doctor_name: str, patient_id: str, medicines: list, notes: str = ""):
    try:
        rec = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "doctor_name": doctor_name,
            "prescription_date": date.today().isoformat(),
            "medicines": medicines,
            "notes": notes,
            "status": "Needs Verification",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        with_retry(lambda: db.table("prescriptions").insert(rec).execute())()
        return True
    except Exception as e:
        logger.error(f"[DoctorAgent] save_prescription error: {e}")
        return False

# ─────────────────────────────────────────────
# Message formatters
# ─────────────────────────────────────────────

def _fmt_patient_profile(p: dict) -> str:
    allergies = p.get("allergies") or []
    if isinstance(allergies, list):
        allergies = ", ".join(allergies) if allergies else "None"
    chronic = p.get("chronic_diseases") or []
    if isinstance(chronic, list):
        chronic = ", ".join(chronic) if chronic else "None"

    dob = p.get("dob", "N/A")
    gender = p.get("gender", "N/A")
    blood = p.get("blood_group", "N/A")
    mobile = p.get("mobile_number", "N/A")

    return (
        f"👤 *{p.get('name', 'Unknown')}*\n"
        f"📱 {mobile}\n"
        f"🎂 DOB: {dob}  |  {gender}  |  🩸 {blood}\n"
        f"⚠️ Allergies: {allergies}\n"
        f"🫀 Chronic: {chronic}\n"
    )

def _fmt_lab_tests(tests: list) -> str:
    if not tests:
        return "No lab tests found."
    lines = ["🧪 *Lab Tests*\n"]
    for t in tests:
        status = t.get("status", "")
        name = t.get("test_name", "")
        test_date = t.get("test_date", "")
        if isinstance(test_date, str):
            test_date = test_date[:10]
        results = t.get("results") or {}
        report_url = t.get("report_url", "")
        result_text = ""
        if isinstance(results, dict) and results:
            result_text = "\n   " + "\n   ".join(f"{k}: {v}" for k, v in list(results.items())[:5])

        lines.append(f"▪️ *{name}* ({test_date}) — _{status}_{result_text}")
        if report_url:
            lines.append(f"   📎 {report_url}")
    return "\n".join(lines)

def _fmt_prescriptions(prescriptions: list) -> str:
    if not prescriptions:
        return "No prescriptions found."
    lines = ["💊 *Prescriptions*\n"]
    for rx in prescriptions:
        rx_date = rx.get("prescription_date", "")
        doctor_name = rx.get("doctor_name", "")
        medicines = rx.get("medicines") or []
        notes = rx.get("notes", "")
        lines.append(f"📅 *{rx_date}* — Dr. {doctor_name}")
        if isinstance(medicines, list):
            for med in medicines:
                if isinstance(med, dict):
                    med_name = med.get("name", med.get("medicine_name", ""))
                    dose = med.get("dose", med.get("dosage", ""))
                    freq = med.get("frequency", "")
                    dur = med.get("duration", "")
                    lines.append(f"   💊 {med_name} — {dose} — {freq} — {dur}")
                else:
                    lines.append(f"   💊 {med}")
        if notes:
            lines.append(f"   📝 Notes: {notes}")
        lines.append("")
    return "\n".join(lines)

def _fmt_reports(reports: list) -> str:
    if not reports:
        return "No reports found."
    lines = ["📋 *Medical Reports*\n"]
    for rep in reports:
        rep_type = rep.get("report_type", "Report")
        rep_date = rep.get("report_date", "")
        ai_summary = rep.get("ai_summary", "")
        ai_rec = rep.get("ai_recommendation", "")
        report_url = rep.get("report_url", "")
        lines.append(f"🗂 *{rep_type}* ({rep_date})")
        if ai_summary:
            lines.append(f"   🤖 {ai_summary}")
        if ai_rec:
            lines.append(f"   💡 {ai_rec}")
        if report_url:
            lines.append(f"   📎 {report_url}")
        lines.append("")
    return "\n".join(lines)

# ─────────────────────────────────────────────
# Interactive message builders
# ─────────────────────────────────────────────

def _main_menu_payload(doctor_name: str) -> dict:
    """WhatsApp interactive list message — main menu."""
    return {
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": f"👨‍⚕️ Dr. {doctor_name}"},
            "body": {"text": "Welcome! What would you like to do?"},
            "footer": {"text": "DoctorBot • Powered by Aatomate"},
            "action": {
                "button": "Open Menu",
                "sections": [
                    {
                        "title": "Patients",
                        "rows": [
                            {"id": "TODAY_PATIENTS", "title": "📅 Today's Patients", "description": "View today's scheduled patients"},
                            {"id": "SEARCH_PATIENT", "title": "🔍 Search Patient", "description": "Search any patient by name or mobile"},
                        ]
                    }
                ]
            }
        }
    }

def _patient_action_payload(patient_name: str) -> dict:
    """Action buttons for a selected patient."""
    return {
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": f"👤 {patient_name}"},
            "body": {"text": "What do you need?"},
            "footer": {"text": "Select an option below"},
            "action": {
                "button": "Actions",
                "sections": [
                    {
                        "title": "Medical Records",
                        "rows": [
                            {"id": "ACTION_LABS", "title": "🧪 Lab Tests", "description": "Latest test results"},
                            {"id": "ACTION_PRESCRIPTIONS", "title": "💊 Prescriptions", "description": "Past prescriptions"},
                            {"id": "ACTION_REPORTS", "title": "📋 Reports", "description": "Medical reports & summaries"},
                        ]
                    },
                    {
                        "title": "Prescription & Status",
                        "rows": [
                            {"id": "ACTION_WRITE_RX", "title": "📝 Write Prescription", "description": "Create a new prescription"},
                            {"id": "ACTION_MARK_DONE", "title": "✅ Mark Completed", "description": "Mark appointment as done"},
                            {"id": "ACTION_MARK_NOSHOW", "title": "❌ Mark No-Show", "description": "Patient didn't show up"},
                            {"id": "ACTION_BACK", "title": "⬅️ Back to Menu", "description": "Return to main menu"},
                        ]
                    }
                ]
            }
        }
    }

# ─────────────────────────────────────────────
# Main DoctorAgent class
# ─────────────────────────────────────────────

class DoctorAgent:
    def __init__(self, account: WhatsAppAccount, sender: WhatsAppSender):
        self.account = account
        self.sender = sender
        self.tenant_id = account.tenant_id

    def process_message(self, body: Dict[Any, Any]):
        logger.info(f"[DoctorAgent] Processing message for tenant {self.tenant_id}")

        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if "messages" not in value:
                    continue

                for msg in value["messages"]:
                    from_number = msg.get("from")
                    if not from_number:
                        continue
                    self._handle_single_message(from_number, msg)

    def _handle_single_message(self, from_number: str, msg: dict):
        session = _get_session(from_number)

        # ── Identify doctor ──────────────────────────────────────
        doctor = session.get("doctor")
        if not doctor:
            doctor = DoctorService.get_doctor_by_whatsapp_number(from_number)
            if not doctor:
                self.sender.send_message(
                    from_number,
                    "⚠️ Your WhatsApp number is not registered as a doctor in this system.\n"
                    "Please contact the hospital admin to add your number to your profile."
                )
                return
            session["doctor"] = doctor

        msg_type = msg.get("type", "")

        # ── Interactive list reply (user tapped a menu option) ───
        if msg_type == "interactive":
            inter = msg.get("interactive", {})
            inter_type = inter.get("type", "")
            if inter_type == "list_reply":
                reply_id = inter.get("list_reply", {}).get("id", "")
                self._handle_list_reply(from_number, session, doctor, reply_id)
                return
            elif inter_type == "button_reply":
                reply_id = inter.get("button_reply", {}).get("id", "")
                self._handle_list_reply(from_number, session, doctor, reply_id)
                return

        # ── Text messages ────────────────────────────────────────
        if msg_type == "text":
            text = msg.get("text", {}).get("body", "").strip()
            self._handle_text(from_number, session, doctor, text)
            
        elif msg_type in ("image", "document"):
            media_obj = msg.get(msg_type, {})
            media_id = media_obj.get("id", "")
            mime_type = media_obj.get("mime_type", "image/jpeg")
            
            patient_id = session.get("selected_patient_id")
            if not patient_id:
                self.sender.send_message(from_number, "❌ No patient selected. Type *menu* to start, select a patient, then upload the report.")
                return
                
            if media_id:
                self.sender.send_message(from_number, "⏳ Uploading and processing medical report...")
                import threading
                threading.Thread(
                    target=self._process_whatsapp_media_report,
                    args=(from_number, media_id, mime_type, patient_id, self.tenant_id)
                ).start()
            else:
                self.sender.send_message(from_number, "❌ Could not receive the file. Please try again.")

    # ── List / Button reply handler ──────────────────────────────

    def _handle_list_reply(self, from_number: str, session: dict, doctor, reply_id: str):
        if reply_id == "TODAY_PATIENTS":
            self._show_today_patients(from_number, session, doctor)

        elif reply_id == "SEARCH_PATIENT":
            session["flow"] = "SEARCHING"
            self.sender.send_message(from_number,
                "🔍 *Search Patient*\n\nType the patient's *name* or *mobile number* to search:")

        elif reply_id == "ACTION_LABS":
            self._show_labs(from_number, session, doctor)

        elif reply_id == "ACTION_PRESCRIPTIONS":
            self._show_prescriptions(from_number, session, doctor)

        elif reply_id == "ACTION_REPORTS":
            self._show_reports(from_number, session, doctor)

        elif reply_id == "ACTION_WRITE_RX":
            self._start_prescription_flow(from_number, session, doctor)

        elif reply_id == "ACTION_MARK_DONE":
            self._mark_appointment(from_number, session, doctor, "completed")

        elif reply_id == "ACTION_MARK_NOSHOW":
            self._mark_appointment(from_number, session, doctor, "no show")

        elif reply_id == "ACTION_BACK":
            _clear_session(from_number)
            session = _get_session(from_number)
            session["doctor"] = doctor
            self.sender.send_interactive_message(from_number, _main_menu_payload(doctor.name))

        elif reply_id.startswith("PAT_"):
            parts = reply_id[4:].split("::")
            patient_id = parts[0]
            self._select_patient(from_number, session, doctor, patient_id)

    # ── Text handler (handles flows & free-text) ─────────────────

    def _handle_text(self, from_number: str, session: dict, doctor, text: str):
        flow = session.get("flow")
        lower = text.lower().strip()

        # ── Reset / greeting ──
        if lower in ("hi", "hello", "menu", "start", "hii", "hey"):
            _clear_session(from_number)
            session = _get_session(from_number)
            session["doctor"] = doctor
            self.sender.send_interactive_message(from_number, _main_menu_payload(doctor.name))
            return

        # ── Patient search flow ──
        if flow == "SEARCHING":
            results = _search_patients(self.tenant_id, text)
            if not results:
                self.sender.send_message(from_number,
                    f"❌ No patients found for *\"{text}\"*.\nTry a different name or number, or type *menu* to go back.")
                return
            session["search_results"] = results
            session["flow"] = "SELECT_SEARCH_PATIENT"
            lines = [f"Found *{len(results)}* patient(s). Reply with the number to select:\n"]
            for i, p in enumerate(results, 1):
                lines.append(f"{i}. {p['name']} — 📱 {p.get('mobile_number', 'N/A')}")
            lines.append("\nOr type *menu* to go back.")
            self.sender.send_message(from_number, "\n".join(lines))
            return

        if flow == "SELECT_SEARCH_PATIENT":
            results = session.get("search_results", [])
            if text.isdigit():
                idx = int(text) - 1
                if 0 <= idx < len(results):
                    patient_id = results[idx]["id"]
                    self._select_patient(from_number, session, doctor, patient_id)
                    return
            self.sender.send_message(from_number,
                "❓ Please reply with a valid number from the list, or type *menu* to go back.")
            return

        # ── Today's patient selection by number ──
        if flow == "SELECT_TODAY_PATIENT":
            appts = session.get("today_appts", [])
            if text.isdigit():
                idx = int(text) - 1
                if 0 <= idx < len(appts):
                    appt = appts[idx]
                    patient_id = appt.get("patient_id") or (appt.get("patients") or {}).get("id")
                    if patient_id:
                        self._select_patient(from_number, session, doctor, patient_id)
                        return
            self.sender.send_message(from_number,
                "❓ Please reply with a valid number from the list, or type *menu* to go back.")
            return

        # ── Prescription writing flow ──
        if flow and flow.startswith("RX_"):
            self._handle_prescription_flow(from_number, session, doctor, text)
            return

        # ── Fallback ──
        self.sender.send_interactive_message(from_number, _main_menu_payload(doctor.name))

    # ── Today's Patients ─────────────────────────────────────────

    def _show_today_patients(self, from_number: str, session: dict, doctor):
        appts = _get_today_appointments(self.tenant_id, doctor.id)
        if not appts:
            self.sender.send_message(from_number,
                f"📅 No appointments scheduled for today ({date.today().strftime('%d %b %Y')}).\n\nType *menu* to go back.")
            return

        session["today_appts"] = appts
        session["flow"] = "" # Clear text-based flow since it's interactive now

        # WhatsApp List max is 10 rows. Chunking appts if > 10.
        chunks = [appts[i:i + 10] for i in range(0, len(appts), 10)]
        for idx, chunk in enumerate(chunks):
            rows = []
            for appt in chunk:
                patient_info = appt.get("patients") or {}
                patient_name = patient_info.get("name") or "Patient"
                appt_time = appt.get("appointment_time", "")[:5]
                status = appt.get("status", "")
                is_ret = appt.get("is_returning", False)
                
                # Check enum value properly
                if status == "completed":
                    status_icon = "✅"
                elif status in ("cancelled", "no show"):
                    status_icon = "❌"
                else:
                    status_icon = "⏳"
                    
                ret_icon = "🔄 " if is_ret else ""
                
                title = f"{appt_time} - {patient_name}"[:24]
                desc = f"{status_icon} {ret_icon}{status.capitalize()}"
                
                rows.append({
                    "id": f"PAT_{appt.get('patient_id', '')}::{appt.get('id', '')}",
                    "title": title,
                    "description": desc[:72]
                })
                
            header_text = f"📅 Today's Patients"
            if len(chunks) > 1:
                header_text += f" ({idx*10 + 1}-{idx*10 + len(chunk)})"
                
            payload = {
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "header": {"type": "text", "text": header_text},
                    "body": {"text": f"Showing {len(chunk)} patient(s) for {date.today().strftime('%d %b')}. Select a patient to view details & actions."},
                    "action": {
                        "button": "View Patients",
                        "sections": [
                            {
                                "title": "Appointments",
                                "rows": rows
                            }
                        ]
                    }
                }
            }
            self.sender.send_interactive_message(from_number, payload)

    # ── Select and show a patient ────────────────────────────────

    def _select_patient(self, from_number: str, session: dict, doctor, patient_id: str):
        patient = _get_patient(patient_id)
        if not patient:
            self.sender.send_message(from_number, "❌ Could not fetch patient details. Type *menu* to go back.")
            return
        session["selected_patient_id"] = patient_id
        session["selected_patient_name"] = patient.get("name", "Patient")
        session["flow"] = "PATIENT_MENU"

        profile_text = _fmt_patient_profile(patient)
        self.sender.send_message(from_number, profile_text)
        self.sender.send_interactive_message(from_number,
            _patient_action_payload(patient.get("name", "Patient")))

    # ── Labs ─────────────────────────────────────────────────────

    def _show_labs(self, from_number: str, session: dict, doctor):
        patient_id = session.get("selected_patient_id")
        patient_name = session.get("selected_patient_name", "Patient")
        if not patient_id:
            self.sender.send_message(from_number, "❌ No patient selected. Type *menu* to start over.")
            return
        tests = _get_lab_tests(self.tenant_id, patient_id)
        self.sender.send_message(from_number, _fmt_lab_tests(tests))
        self.sender.send_message(from_number, "📸 *To upload a new Lab Test or Report for this patient, simply send a Photo or PDF right now.*")
        # Re-show action menu
        self.sender.send_interactive_message(from_number, _patient_action_payload(patient_name))

    # ── Prescriptions ────────────────────────────────────────────

    def _show_prescriptions(self, from_number: str, session: dict, doctor):
        patient_id = session.get("selected_patient_id")
        patient_name = session.get("selected_patient_name", "Patient")
        if not patient_id:
            self.sender.send_message(from_number, "❌ No patient selected. Type *menu* to start over.")
            return
        prescriptions = _get_prescriptions(self.tenant_id, patient_id)
        self.sender.send_message(from_number, _fmt_prescriptions(prescriptions))
        self.sender.send_interactive_message(from_number, _patient_action_payload(patient_name))

    # ── Reports ──────────────────────────────────────────────────

    def _show_reports(self, from_number: str, session: dict, doctor):
        patient_id = session.get("selected_patient_id")
        patient_name = session.get("selected_patient_name", "Patient")
        if not patient_id:
            self.sender.send_message(from_number, "❌ No patient selected. Type *menu* to start over.")
            return
        reports = _get_reports(self.tenant_id, patient_id)
        self.sender.send_message(from_number, _fmt_reports(reports))
        self.sender.send_message(from_number, "📸 *To upload a new Lab Test or Report for this patient, simply send a Photo or PDF right now.*")
        self.sender.send_interactive_message(from_number, _patient_action_payload(patient_name))

    # ── Mark appointment status ──────────────────────────────────

    def _mark_appointment(self, from_number: str, session: dict, doctor, status: str):
        patient_id = session.get("selected_patient_id")
        patient_name = session.get("selected_patient_name", "Patient")
        if not patient_id:
            self.sender.send_message(from_number, "❌ No patient selected. Type *menu* to start over.")
            return
        appt = _get_patient_appointment_today(self.tenant_id, doctor.id, patient_id)
        if not appt:
            self.sender.send_message(from_number,
                f"⚠️ No appointment found today for *{patient_name}*.\n"
                "(You can still view their records above.)")
            self.sender.send_interactive_message(from_number, _patient_action_payload(patient_name))
            return
        ok = _update_appointment_status(self.tenant_id, appt["id"], status)
        icon = "✅" if status == "completed" else "❌"
        if ok:
            self.sender.send_message(from_number,
                f"{icon} Appointment for *{patient_name}* marked as *{status}*.")
        else:
            self.sender.send_message(from_number, "⚠️ Failed to update appointment status. Please try again.")
        self.sender.send_interactive_message(from_number, _patient_action_payload(patient_name))

    # ── Write Prescription Flow ──────────────────────────────────
    # Flow steps: RX_MEDICINE_NAME → RX_DOSE → RX_FREQUENCY → RX_DURATION → RX_NOTES → RX_CONFIRM → RX_MORE

    def _start_prescription_flow(self, from_number: str, session: dict, doctor):
        patient_id = session.get("selected_patient_id")
        if not patient_id:
            self.sender.send_message(from_number, "❌ No patient selected. Type *menu* to start over.")
            return
        session["flow"] = "RX_MEDICINE_NAME"
        session["rx_medicines"] = []
        session["rx_current"] = {}
        self.sender.send_message(from_number,
            f"📝 *New Prescription*\nPatient: *{session.get('selected_patient_name', '')}*\n\n"
            "Let's add medicines one by one.\n\n"
            "💊 Enter *medicine name* (or type *done* to finish):")

    def _handle_prescription_flow(self, from_number: str, session: dict, doctor, text: str):
        flow = session.get("flow")
        lower = text.lower().strip()

        # Allow "cancel" anywhere in prescription flow
        if lower == "cancel":
            session["flow"] = "PATIENT_MENU"
            self.sender.send_message(from_number, "❌ Prescription cancelled.")
            self.sender.send_interactive_message(from_number,
                _patient_action_payload(session.get("selected_patient_name", "Patient")))
            return

        if flow == "RX_MEDICINE_NAME":
            if lower == "done":
                self._finish_prescription(from_number, session, doctor)
                return
            session["rx_current"] = {"name": text}
            session["flow"] = "RX_DOSE"
            self.sender.send_message(from_number,
                f"✅ Medicine: *{text}*\n\n📏 Enter *dose* (e.g. 500mg, 1 tablet):")

        elif flow == "RX_DOSE":
            session["rx_current"]["dose"] = text
            session["flow"] = "RX_FREQUENCY"
            self.sender.send_message(from_number,
                f"✅ Dose: *{text}*\n\n🔁 Enter *frequency* (e.g. twice daily, 1-0-1, after meals):")

        elif flow == "RX_FREQUENCY":
            session["rx_current"]["frequency"] = text
            session["flow"] = "RX_DURATION"
            self.sender.send_message(from_number,
                f"✅ Frequency: *{text}*\n\n📆 Enter *duration* (e.g. 5 days, 1 week):")

        elif flow == "RX_DURATION":
            session["rx_current"]["duration"] = text
            # Add this medicine to the list
            medicine = dict(session["rx_current"])
            session["rx_medicines"].append(medicine)
            session["rx_current"] = {}
            session["flow"] = "RX_MEDICINE_NAME"
            meds_count = len(session["rx_medicines"])
            self.sender.send_message(from_number,
                f"✅ *{medicine['name']}* added! ({meds_count} medicine(s) so far)\n\n"
                f"💊 Enter next *medicine name*, or type *done* to finish the prescription:")

        elif flow == "RX_CONFIRM":
            if lower in ("yes", "confirm", "y"):
                medicines = session.get("rx_medicines", [])
                notes = session.get("rx_notes", "")
                patient_id = session.get("selected_patient_id")
                ok = _save_prescription(
                    self.tenant_id, doctor.id, doctor.name,
                    patient_id, medicines, notes
                )
                if ok:
                    self.sender.send_message(from_number,
                        f"✅ *Prescription saved successfully!*\n\n"
                        f"Patient: *{session.get('selected_patient_name')}*\n"
                        f"Medicines: {len(medicines)}\n"
                        f"Status: Needs Verification\n\n"
                        "The prescription is now in the system for verification.")
                else:
                    self.sender.send_message(from_number,
                        "⚠️ Failed to save prescription. Please try again from the patient menu.")
                session["flow"] = "PATIENT_MENU"
                self.sender.send_interactive_message(from_number,
                    _patient_action_payload(session.get("selected_patient_name", "Patient")))
            elif lower in ("no", "n", "cancel"):
                session["flow"] = "PATIENT_MENU"
                self.sender.send_message(from_number, "❌ Prescription cancelled.")
                self.sender.send_interactive_message(from_number,
                    _patient_action_payload(session.get("selected_patient_name", "Patient")))
            else:
                self.sender.send_message(from_number, "Please reply *yes* to confirm or *no* to cancel.")

    def _finish_prescription(self, from_number: str, session: dict, doctor):
        medicines = session.get("rx_medicines", [])
        if not medicines:
            self.sender.send_message(from_number,
                "⚠️ No medicines added yet. Enter at least one medicine name, or type *cancel*.")
            return

        # Build a summary for confirmation
        lines = [f"📋 *Prescription Summary*\nPatient: *{session.get('selected_patient_name')}*\n"]
        for i, med in enumerate(medicines, 1):
            lines.append(
                f"{i}. 💊 *{med.get('name')}*\n"
                f"   Dose: {med.get('dose')} | Freq: {med.get('frequency')} | Duration: {med.get('duration')}"
            )
        lines.append("\nType *yes* to save, or *no* to cancel.")

        session["flow"] = "RX_CONFIRM"
        self.sender.send_message(from_number, "\n".join(lines))

    def _download_whatsapp_media(self, media_id: str) -> tuple:
        import requests as _requests
        try:
            meta_url = f"https://graph.facebook.com/v20.0/{media_id}"
            meta_resp = _requests.get(
                meta_url,
                headers={"Authorization": f"Bearer {self.sender.access_token}"},
                timeout=10,
            )
            if meta_resp.status_code != 200:
                return None, None
            meta = meta_resp.json()
            download_url = meta.get("url", "")
            mime_type = meta.get("mime_type", "image/jpeg")

            file_resp = _requests.get(
                download_url,
                headers={"Authorization": f"Bearer {self.sender.access_token}"},
                timeout=30,
            )
            if file_resp.status_code == 200:
                return file_resp.content, mime_type
            return None, None
        except Exception:
            return None, None

    def _process_whatsapp_media_report(self, to_number: str, media_id: str, mime_type: str, patient_id: str, tenant_id: str):
        try:
            from app.services.report_service import ReportService
            from app.schemas.report import MedicalReportCreate, ReportStatus

            image_bytes, actual_mime = self._download_whatsapp_media(media_id)
            if not image_bytes:
                self.sender.send_message(to_number, "❌ Failed to download your file. Please try again.")
                return

            mime = actual_mime or mime_type

            report_in = MedicalReportCreate(
                patient_id=patient_id,
                status=ReportStatus.PENDING,
                uploaded_by="doctor",
                wa_media_id=media_id,
                wa_mime_type=mime,
            )
            report = ReportService.create_report(tenant_id, report_in)

            # Run AI processing
            ReportService.process_report_async(tenant_id, report.id, image_bytes, mime)

            updated = ReportService.get_report(tenant_id, report.id)
            if not updated or updated.status != ReportStatus.PROCESSED:
                self.sender.send_message(to_number, "⚠️ Report saved but AI extraction took longer than expected.")
                return

            self.sender.send_message(to_number, f"✅ Medical report processed successfully and saved to the patient's record!")
        except Exception as e:
            self.sender.send_message(to_number, f"❌ Error processing report.")
