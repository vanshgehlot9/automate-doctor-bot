from fastapi import APIRouter, Request, Response, HTTPException, BackgroundTasks
from app.core.config import settings
from app.services.ai_receptionist import AIReceptionist
from app.core.crypto import (
    decrypt_whatsapp_flow_request,
    encrypt_whatsapp_flow_response,
    get_public_key_fingerprint,
    get_keyring_status,
    invalidate_key_cache,
    PRIVATE_KEY_PATH,
    PUBLIC_KEY_PATH,
)
from typing import Dict, Any
import requests as _requests
import logging
import os
import time
import json
import base64
from datetime import date, datetime, timedelta
from app.services.doctor_service import DoctorService
from app.services.schedule_service import ScheduleService
from app.services.appointment_service import AppointmentService
from app.schemas.appointment import AppointmentCreate, AppointmentStatus

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Constants ──────────────────────────────────────────────────────────────────
WA_API_VERSION = "v20.0"
_ROOT     = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
DEBUG_LOG = os.path.join(_ROOT, "whatsapp_debug.log")

# ── Message deduplication (in-memory) ────────────────────────────────────────
_processed_message_ids: Dict[str, float] = {}
_DEDUP_TTL = 300

def _is_duplicate(mid: str) -> bool:
    now = time.time()
    expired = [k for k, v in _processed_message_ids.items() if now - v > _DEDUP_TTL]
    for k in expired:
        del _processed_message_ids[k]
    if mid in _processed_message_ids:
        return True
    _processed_message_ids[mid] = now
    return False

def _debug_log(msg: str):
    logger.info(msg)
    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

# ── WhatsApp send helpers ──────────────────────────────────────────────────────
def send_whatsapp_message(to_number: str, text: str, phone_number_id: str) -> bool:
    if not settings.WHATSAPP_TOKEN or not phone_number_id:
        logger.error("[send] WHATSAPP_TOKEN or phone_number_id missing.")
        return False
    url = f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text, "preview_url": False},
    }
    try:
        resp = _requests.post(
            url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json=payload, timeout=10,
        )
        _debug_log(f"[send] TO={to_number} STATUS={resp.status_code} BODY={resp.text[:200]}")
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"[send] Exception: {e}")
        return False

def send_whatsapp_reaction(to_number: str, message_id: str, emoji: str, phone_number_id: str):
    if not settings.WHATSAPP_TOKEN or not phone_number_id:
        return
    try:
        _requests.post(
            f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json={"messaging_product": "whatsapp", "recipient_type": "individual",
                  "to": to_number, "type": "reaction",
                  "reaction": {"message_id": message_id, "emoji": emoji}},
            timeout=5,
        )
    except Exception:
        pass

# ── WhatsApp Flow CTA Helper ────────────────────────────────────────────────────
def send_flow_cta_message(to_number: str, phone_number_id: str, profile_name: str = "") -> bool:
    if not settings.WHATSAPP_TOKEN or not phone_number_id:
        logger.error("[send CTA] Missing token or phone_number_id")
        return False
        
    flow_id = os.environ.get("WHATSAPP_FLOW_ID", "1569884864659929")
    
    # Compact state payload serialized into URL-Safe Base64 flow_token
    state = {"p": to_number, "n": profile_name[:30], "f": "clinic"}
    encoded_state = base64.urlsafe_b64encode(json.dumps(state).encode()).decode().rstrip("=")
    flow_token = f"tk_{encoded_state}"
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "flow",
            "header": {
                "type": "text",
                "text": "Book Your Appointment 🏥"
            },
            "body": {
                "text": "Welcome to *Aatomate LLP Clinic*! \n\nTap below to book an appointment with our specialists."
            },
            "footer": {
                "text": "Secure Medical Booking"
            },
            "action": {
                "name": "flow",
                "parameters": {
                    "flow_message_version": "3",
                    "flow_token": flow_token,
                    "flow_id": flow_id,
                    "flow_cta": "Book Appointment",
                    "mode": "published",
                    "flow_action": "data_exchange"
                }
            }
        }
    }
    url = f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages"
    try:
        resp = _requests.post(
            url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json=payload, timeout=10,
        )
        _debug_log(f"[send CTA] TO={to_number} STATUS={resp.status_code}")
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"[send CTA] Exception: {e}")
        return False

def send_patient_classification_message(to_number: str, phone_number_id: str) -> bool:
    if not settings.WHATSAPP_TOKEN or not phone_number_id:
        return False
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": "Are you an existing patient or a new patient?"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "patient_existing",
                            "title": "Existing Patient"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "patient_new",
                            "title": "New Patient"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "patient_guest",
                            "title": "Guest Booking"
                        }
                    }
                ]
            }
        }
    }
    url = f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages"
    try:
        resp = _requests.post(
            url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json=payload, timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"[send classification] Exception: {e}")
        return False

def send_existing_profiles_message(to_number: str, phone_number_id: str, patients: list, profile_name: str = "") -> bool:
    """Send a list of existing patient profiles found by phone number, plus 'Register New'."""
    if not settings.WHATSAPP_TOKEN or not phone_number_id:
        return False
    
    rows = []
    for i, p in enumerate(patients[:9]):  # WhatsApp list max 10 rows, reserve 1 for 'New'
        name = getattr(p, 'name', 'Patient')
        gender = getattr(p, 'gender', '')
        dob = str(getattr(p, 'dob', ''))
        pid = str(getattr(p, 'id', ''))
        desc = f"{gender}"
        if dob:
            desc += f" • DOB: {dob}"
        rows.append({
            "id": f"select_patient_{pid}",
            "title": name[:24],
            "description": desc[:72]
        })
    
    # Always add a "Register New Patient" option at the end
    rows.append({
        "id": "patient_new",
        "title": "➕ Register New Patient",
        "description": "Create a new patient profile"
    })
    
    count = len(patients)
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": f"Your Profiles ({count} found) 👤"
            },
            "body": {
                "text": f"We found *{count} patient profile(s)* registered with your number.\n\nPlease select who you'd like to book for, or register a new patient."
            },
            "footer": {
                "text": "Secure Patient Selection"
            },
            "action": {
                "button": "Select Patient",
                "sections": [
                    {
                        "title": "Patient Profiles",
                        "rows": rows
                    }
                ]
            }
        }
    }
    url = f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages"
    try:
        resp = _requests.post(
            url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json=payload, timeout=10,
        )
        _debug_log(f"[send profiles] TO={to_number} profiles={count} STATUS={resp.status_code}")
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"[send profiles] Exception: {e}")
        return False

def send_registration_flow_cta_message(to_number: str, phone_number_id: str, profile_name: str = "") -> bool:
    if not settings.WHATSAPP_TOKEN or not phone_number_id:
        return False
        
    flow_id = os.environ.get("WHATSAPP_REGISTRATION_FLOW_ID", "1336906358510282")
    
    state = {"p": to_number, "n": profile_name[:30], "f": "register"}
    import json, base64
    encoded_state = base64.urlsafe_b64encode(json.dumps(state).encode()).decode().rstrip("=")
    flow_token = f"tk_{encoded_state}"
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "flow",
            "header": {
                "type": "text",
                "text": "New Patient Registration 🏥"
            },
            "body": {
                "text": "Welcome! Please complete your registration."
            },
            "footer": {
                "text": "Secure Registration"
            },
            "action": {
                "name": "flow",
                "parameters": {
                    "flow_message_version": "3",
                    "flow_token": flow_token,
                    "flow_id": flow_id,
                    "flow_cta": "Register Now",
                    "mode": "published",
                    "flow_action": "data_exchange"
                }
            }
        }
    }
    url = f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages"
    try:
        resp = _requests.post(
            url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json=payload, timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"[send CTA] Exception: {e}")
        return False

def send_main_menu_message(to_number: str, phone_number_id: str) -> bool:
    if not settings.WHATSAPP_TOKEN or not phone_number_id:
        return False
        
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": "Welcome to Aatomate Clinic 🏥"
            },
            "body": {
                "text": "Hello! How can we help you today? Please select an option from our main menu."
            },
            "footer": {
                "text": "Secure Medical Services"
            },
            "action": {
                "button": "Main Menu",
                "sections": [
                    {
                        "title": "Services",
                        "rows": [
                            {"id": "menu_book_appointment", "title": "Book Appointment"},
                            {"id": "menu_reports", "title": "Reports"},
                            {"id": "menu_prescriptions", "title": "Prescriptions"},
                            {"id": "menu_lab_test", "title": "Lab Test"},
                            {"id": "menu_emergency", "title": "Emergency"},
                            {"id": "menu_talk_to_ai", "title": "Talk to AI"}
                        ]
                    }
                ]
            }
        }
    }
    url = f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages"
    try:
        resp = _requests.post(
            url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json=payload, timeout=10,
        )
        _debug_log(f"[send menu] TO={to_number} STATUS={resp.status_code}")
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"[send menu] Exception: {e}")
        return False

def send_success_messages(to_number: str, phone_number_id: str, doctor_id: str, tenant_id: str = None):
    if not settings.WHATSAPP_TOKEN or not phone_number_id:
        return
    
    if not tenant_id:
        tenant_id = settings.DEFAULT_TENANT_ID
        
    from app.services.tenant_service import TenantService
    from app.services.doctor_service import DoctorService
    
    tenant = TenantService.get_tenant(tenant_id)
    doctor_obj = DoctorService.get_doctor(tenant_id, doctor_id) if doctor_id else None
    
    doctor_name = doctor_obj.name if doctor_obj else "Doctor"
    clinic_name = tenant.hospital_name if tenant else "Aatomate Clinic"
    clinic_address = tenant.clinic_address if tenant and tenant.clinic_address else "Address not provided"
    room_floor = tenant.room_floor if tenant and tenant.room_floor else "Check at Reception"
    lat = tenant.latitude if tenant and tenant.latitude else 28.6139
    lng = tenant.longitude if tenant and tenant.longitude else 77.2090
        
    url = f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    
    text = (
        "✅ *Appointment Confirmed!*\n\n"
        f"👨‍⚕️ {doctor_name}\n"
        f"🏥 {clinic_name}\n"
        f"🏢 {room_floor}\n\n"
        "Please arrive 10 minutes early."
    )
    _requests.post(url, headers=headers, json={"messaging_product": "whatsapp", "to": to_number, "type": "text", "text": {"body": text}})
    
    loc_payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "location",
        "location": {
            "longitude": lng,
            "latitude": lat,
            "name": clinic_name,
            "address": clinic_address
        }
    }
    _requests.post(url, headers=headers, json=loc_payload)
    
    list_payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": { "type": "text", "text": "Manage Appointment" },
            "body": { "text": "Select an action below:" },
            "footer": { "text": "Options" },
            "action": {
                "button": "Options",
                "sections": [
                    {
                        "title": "Actions",
                        "rows": [
                            {"id": "action_calendar", "title": "Add to Calendar", "description": "Save to your schedule"},
                            {"id": "action_pdf", "title": "Download PDF", "description": "Get appointment receipt"},
                            {"id": "action_reschedule", "title": "Reschedule", "description": "Change date/time"},
                            {"id": "action_cancel", "title": "Cancel", "description": "Cancel appointment"}
                        ]
                    }
                ]
            }
        }
    }
    _requests.post(url, headers=headers, json=list_payload)

# ── Reports helpers ───────────────────────────────────────────────────────────

def _send_prescriptions_submenu(to_number: str, phone_number_id: str):
    """Send the Prescriptions sub-menu as a list message."""
    if not settings.WHATSAPP_TOKEN or not phone_number_id:
        return
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Prescription Center 📋"},
            "body": {"text": "Please choose an option."},
            "footer": {"text": "Manage your medicines securely."},
            "action": {
                "button": "Options",
                "sections": [
                    {
                        "title": "My Prescriptions",
                        "rows": [
                            {"id": "rx_active", "title": "🟢 Active Prescriptions", "description": "View current medicines"},
                            {"id": "rx_previous", "title": "📁 Previous Prescriptions", "description": "View past history"},
                            {"id": "rx_download", "title": "⬇️ Download Prescription", "description": "Get PDF copy"},
                        ]
                    },
                    {
                        "title": "Medicine Management",
                        "rows": [
                            {"id": "rx_schedule", "title": "⏰ Medicine Schedule", "description": "Today's timings"},
                            {"id": "rx_refill", "title": "💊 Request Refill", "description": "Send to pharmacy"},
                            {"id": "rx_ask_ai", "title": "🤖 Ask About Medicine", "description": "AI Assistant"},
                        ]
                    },
                    {
                        "title": "Other",
                        "rows": [
                            {"id": "menu_book_appointment_direct", "title": "📅 Book Follow-up"},
                            {"id": "menu_main", "title": "🏠 Home"},
                        ]
                    }
                ]
            }
        }
    }
    url = f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages"
    try:
        _requests.post(url, headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}", "Content-Type": "application/json"}, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"[prescriptions_submenu] {e}")


def _send_dynamic_prescription_list(to_number: str, phone_number_id: str, prescriptions: list, action_prefix: str, header_text: str, body_text: str):
    """Dynamically generates a WhatsApp List message of prescriptions."""
    if not settings.WHATSAPP_TOKEN or not phone_number_id:
        return
        
    if not prescriptions:
        send_whatsapp_message(to_number, "No prescriptions found.", phone_number_id)
        return
        
    rows = []
    for i, p in enumerate(prescriptions[:10]): # Max 10 items in a section
        doc = p.doctor_name.value if p.doctor_name else "Doctor"
        dt = p.prescription_date.value if p.prescription_date else p.created_at.strftime("%d %b %Y")
        med_count = len(p.medicines)
        rows.append({
            "id": f"{action_prefix}_{p.id}",
            "title": f"{doc} - {dt}"[:24],
            "description": f"{med_count} medicines"[:72]
        })
        
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": header_text},
            "body": {"text": body_text},
            "action": {
                "button": "Select",
                "sections": [{"title": "Prescriptions", "rows": rows}]
            }
        }
    }
    url = f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages"
    try:
        _requests.post(url, headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}", "Content-Type": "application/json"}, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"[dynamic_rx_list] {e}")


def _send_reports_submenu(to_number: str, phone_number_id: str):
    """Send the Reports sub-menu as a list message."""
    if not settings.WHATSAPP_TOKEN or not phone_number_id:
        return
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Medical Reports 📋"},
            "body": {"text": "Choose an option below:"},
            "footer": {"text": "Your health history, secured."},
            "action": {
                "button": "Options",
                "sections": [
                    {
                        "title": "Reports",
                        "rows": [
                            {"id": "report_upload", "title": "⬆️ Upload New Report", "description": "Photo or PDF"},
                            {"id": "report_timeline", "title": "📅 My Reports", "description": "View your history"},
                            {"id": "report_search", "title": "🔍 Search Reports", "description": "Find by keyword"},
                        ]
                    }
                ]
            }
        }
    }
    url = f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages"
    try:
        _requests.post(
            url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}", "Content-Type": "application/json"},
            json=payload, timeout=10,
        )
    except Exception as e:
        logger.error(f"[reports_submenu] {e}")


def _download_whatsapp_media(media_id: str) -> tuple:
    """Download media bytes from WhatsApp Cloud API. Returns (bytes, mime_type)."""
    try:
        # Step 1: Get media URL
        meta_url = f"https://graph.facebook.com/{WA_API_VERSION}/{media_id}"
        meta_resp = _requests.get(
            meta_url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            timeout=10,
        )
        if meta_resp.status_code != 200:
            raise Exception(f"Media meta fetch failed: {meta_resp.status_code}")
        meta = meta_resp.json()
        download_url = meta.get("url", "")
        mime_type = meta.get("mime_type", "image/jpeg")

        # Step 2: Download actual file bytes
        file_resp = _requests.get(
            download_url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            timeout=30,
        )
        if file_resp.status_code != 200:
            raise Exception(f"Media download failed: {file_resp.status_code}")
        return file_resp.content, mime_type
    except Exception as e:
        logger.error(f"[download_media] {e}")
        return None, None


def _format_report_result_message(report) -> str:
    """Format a processed report into a WhatsApp-friendly confirmation message."""
    lines = [
        f"✅ *Report Detected*\n",
        f"📋 *Type:* {report.report_type}",
        f"🏷️ *Category:* {report.category}",
    ]
    if report.report_date:
        lines.append(f"📅 *Date:* {report.report_date}")
    
    # Key findings from structured_data
    if report.structured_data:
        lines.append("\n*Key Findings:*")
        status_icons = {"Normal": "✅", "Low": "⚠️", "High": "⚠️", "Critical": "🚨"}
        for param, detail in list(report.structured_data.items())[:6]:  # cap at 6
            val = detail.get("value", "—")
            unit = detail.get("unit", "")
            status = detail.get("status", "")
            icon = status_icons.get(status, "•")
            lines.append(f"  {icon} *{param}:* {val} {unit}  _{status}_")
    
    if report.ai_summary:
        lines.append(f"\n🤖 *AI Summary:*\n{report.ai_summary}")
    
    if report.ai_recommendation:
        lines.append(f"\n💡 *Recommendation:*\n{report.ai_recommendation}")
    
    lines.append(f"\n🔖 *Tags:* {', '.join(report.tags) if report.tags else '—'}")
    return "\n".join(lines)


def _process_whatsapp_media_report(
    to_number: str,
    phone_number_id: str,
    media_id: str,
    mime_type: str,
    patient_id: str,
    tenant_id: str,
):
    """
    Background task: download media, run OCR + AI, save report, send result to user.
    """
    try:
        from app.services.report_service import ReportService
        from app.schemas.report import MedicalReportCreate, ReportStatus

        # Download the file
        image_bytes, actual_mime = _download_whatsapp_media(media_id)
        if not image_bytes:
            send_whatsapp_message(to_number, "❌ Failed to download your file. Please try again.", phone_number_id)
            return

        mime = actual_mime or mime_type

        # Create a pending report record
        report_in = MedicalReportCreate(
            patient_id=patient_id,
            status=ReportStatus.PENDING,
            uploaded_by="patient",
            wa_media_id=media_id,
            wa_mime_type=mime,
        )
        report = ReportService.create_report(tenant_id, report_in)

        # Run AI processing inline (since we're already in a background task)
        ReportService.process_report_async(tenant_id, report.id, image_bytes, mime)

        # Fetch the updated report
        updated = ReportService.get_report(tenant_id, report.id)
        if not updated or updated.status != ReportStatus.PROCESSED:
            send_whatsapp_message(to_number, "⚠️ Report processed but AI extraction took longer than expected. Check 'My Reports' in a moment.", phone_number_id)
            return

        # Send the rich confirmation message
        msg = _format_report_result_message(updated)
        send_whatsapp_message(to_number, msg, phone_number_id)

        # Follow-up interactive buttons
        url = f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}", "Content-Type": "application/json"}
        follow_up = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": "What would you like to do next?"},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": "report_timeline", "title": "My Reports"}},
                        {"type": "reply", "reply": {"id": "menu_book_appointment_direct", "title": "Book Appointment"}},
                        {"type": "reply", "reply": {"id": "menu_main", "title": "Main Menu"}},
                    ]
                }
            }
        }
        _requests.post(url, headers=headers, json=follow_up, timeout=10)

    except Exception as e:
        logger.error(f"[process_media_report] Error: {e}")
        send_whatsapp_message(to_number, "❌ Something went wrong while processing your report. Please try again.", phone_number_id)


def _handle_medicine_qa(patient_id: str, question: str, to_number: str, phone_number_id: str, tenant_id: str = None):
    """Answers patient questions using their active prescriptions and Gemini AI."""
    from app.services.prescription_service import PrescriptionService
    import google.generativeai as genai
    import os
    from app.core.config import settings as _settings
    _tid = tenant_id or _settings.DEFAULT_TENANT_ID
    
    active = PrescriptionService.get_active_prescriptions(_tid, patient_id)
    if not active:
        send_whatsapp_message(to_number, "I couldn't find any active prescriptions for you to answer this question. Please upload one first!", phone_number_id)
        return
        
    context = ""
    for p in active:
        context += PrescriptionService.format_prescription_for_whatsapp(p) + "\n\n"
        
    prompt = f"""
    You are a helpful clinical AI assistant for a hospital. A patient has asked a question about their medicine.
    
    PATIENT QUESTION:
    "{question}"
    
    PATIENT'S CURRENT ACTIVE PRESCRIPTIONS:
    {context}
    
    INSTRUCTIONS:
    1. Answer the patient's question clearly and concisely in 2-3 sentences.
    2. ONLY use the provided prescription context and trusted general medical guidance (e.g. standard times to take medicines with/without food).
    3. Do NOT invent new treatment plans or recommend new drugs.
    4. Include a short disclaimer at the end: "*Note: Always consult your doctor for medical advice.*"
    """
    
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            send_whatsapp_message(to_number, "AI services are currently unavailable.", phone_number_id)
            return
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        response = model.generate_content(prompt)
        ai_reply = response.text.strip()
        send_whatsapp_message(to_number, "🤖 " + ai_reply, phone_number_id)
    except Exception as e:
        logger.error(f"[medicine_qa] AI Error: {e}")
        send_whatsapp_message(to_number, "❌ Sorry, I'm having trouble understanding right now. Please try again later.", phone_number_id)


# ── Message processor ─────────────────────────────────────────────────────────
def process_whatsapp_message(body: Dict[Any, Any]):
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if "statuses" in value and "messages" not in value:
                    return
                if "messages" not in value:
                    return
                metadata        = value.get("metadata", {})
                phone_number_id = metadata.get("phone_number_id", "")
                
                # ── MULTI-TENANT ISOLATION ────────────────────────────────────
                # Resolve which hospital/tenant this message belongs to by looking
                # up the WhatsApp phone_number_id. This is the ONLY correct
                # approach for multi-tenant WhatsApp; each hospital has its own
                # registered WhatsApp Business phone number.
                from app.services.tenant_service import TenantService as _TenantService
                _resolved_tenant = _TenantService.get_tenant_by_phone_number_id(phone_number_id)
                tenant_id = _resolved_tenant.id if _resolved_tenant else settings.DEFAULT_TENANT_ID
                if not _resolved_tenant:
                    logger.warning(f"[multi-tenant] No tenant found for phone_number_id={phone_number_id}. Falling back to DEFAULT_TENANT_ID. Register this number in Supabase tenants table.")
                # ─────────────────────────────────────────────────────────────
                
                # Extract profile name
                contacts = value.get("contacts", [])
                profile_name = ""
                if contacts and len(contacts) > 0:
                    profile_name = contacts[0].get("profile", {}).get("name", "")

                for message in value["messages"]:
                    message_id   = message.get("id", "")
                    from_number  = message.get("from", "")
                    message_type = message.get("type", "")
                    if not from_number or not phone_number_id:
                        continue
                    if _is_duplicate(message_id):
                        logger.info(f"[process] Duplicate {message_id}, skipping.")
                        continue
                    _debug_log(f"[process] NEW MSG from={from_number} type={message_type} id={message_id}")
                    if message_type == "text":
                        text_body = message.get("text", {}).get("body", "").strip()
                        if not text_body:
                            continue
                        send_whatsapp_reaction(from_number, message_id, "\U0001f440", phone_number_id)
                        
                        greetings = {"hi", "hello", "hey", "help", "menu", "start", "hii", "helo"}
                        text_lower = text_body.lower()
                        is_greeting = any(text_lower.startswith(g) for g in greetings)
                        is_question = "?" in text_body or any(text_lower.startswith(q) for q in ["can ", "how ", "what ", "why ", "is ", "does ", "do ", "when ", "where ", "should ", "will ", "would "])
                        
                        if not is_greeting and len(text_lower) > 2:
                            if is_question:
                                import threading
                                patient_id = "wa_" + "".join(filter(str.isdigit, from_number))
                                threading.Thread(
                                    target=_handle_medicine_qa,
                                    args=(patient_id, text_body, from_number, phone_number_id, tenant_id)
                                ).start()
                            else:
                                patient_id = "wa_" + "".join(filter(str.isdigit, from_number))
                                from app.services.report_service import ReportService
                                search_results = ReportService.search_reports(
                                    tenant_id, patient_id, text_body, limit=5
                                )
                                if search_results:
                                    lines = ["\U0001f50d *Search Results for \"" + text_body + "\":*\n"]
                                    for r in search_results:
                                        rdate = r.report_date or "\u2014"
                                        lines.append(f"\U0001f4cb *{r.report_type}*  _{rdate}_")
                                        if r.ai_summary:
                                            lines.append(f"  {r.ai_summary[:80]}...")
                                    send_whatsapp_message(from_number, "\n".join(lines), phone_number_id)
                                    send_whatsapp_reaction(from_number, message_id, "\u2705", phone_number_id)
                                else:
                                    ok = send_main_menu_message(from_number, phone_number_id)
                                    if ok:
                                        send_whatsapp_reaction(from_number, message_id, "\u2705", phone_number_id)
                        else:
                            ok = send_main_menu_message(from_number, phone_number_id)
                            if ok:
                                send_whatsapp_reaction(from_number, message_id, "\u2705", phone_number_id)
                            
                    elif message_type == "interactive":
                        interactive = message.get("interactive", {})
                        int_type = interactive.get("type", "")
                        
                        if int_type == "list_reply":
                            list_id = interactive.get("list_reply", {}).get("id", "")
                            if list_id == "menu_book_appointment":
                                send_patient_classification_message(from_number, phone_number_id)
                            elif list_id == "menu_reports":
                                _send_reports_submenu(from_number, phone_number_id)
                            elif list_id == "menu_prescriptions":
                                _send_prescriptions_submenu(from_number, phone_number_id)
                            elif list_id == "menu_lab_test":
                                send_whatsapp_message(from_number, "Lab testing services are coming soon.", phone_number_id)
                            elif list_id == "menu_emergency":
                                send_whatsapp_message(from_number, "🚨 For emergencies, please call 911 or visit the nearest hospital immediately.", phone_number_id)
                            elif list_id == "menu_talk_to_ai":
                                send_whatsapp_message(from_number, "Hello! I am your AI assistant. How can I help you today?", phone_number_id)
                            elif list_id == "action_calendar":
                                send_whatsapp_message(from_number, "📅 Calendar invite (.ics) integration coming soon!", phone_number_id)
                            elif list_id == "action_pdf":
                                send_whatsapp_message(from_number, "📄 PDF receipt will be generated and sent shortly.", phone_number_id)
                            elif list_id == "action_reschedule":
                                send_whatsapp_message(from_number, "🔄 To reschedule, please select Book Appointment again.", phone_number_id)
                            elif list_id == "action_cancel":
                                send_whatsapp_message(from_number, "❌ Your appointment cancellation request has been received.", phone_number_id)
                            elif list_id == "report_upload":
                                send_whatsapp_message(from_number,
                                    "📸 Please send your report as a *photo* or *PDF document*. I'll analyse it with AI instantly!", phone_number_id)
                            elif list_id == "report_timeline":
                                patient_id = "wa_" + "".join(filter(str.isdigit, from_number))
                                from app.services.report_service import ReportService
                                reports = ReportService.get_patient_reports(tenant_id, patient_id, limit=20)
                                timeline_text = ReportService.format_timeline_for_whatsapp(reports)
                                send_whatsapp_message(from_number, timeline_text, phone_number_id)
                            elif list_id == "report_search":
                                send_whatsapp_message(from_number,
                                    "🔍 Type the keyword to search your reports. Examples: *CBC*, *MRI*, *sugar*, *vitamin*", phone_number_id)
                            
                            # ── Prescriptions Handlers ─────────────────────────────────────
                            elif list_id == "rx_active":
                                patient_id = "wa_" + "".join(filter(str.isdigit, from_number))
                                from app.services.prescription_service import PrescriptionService
                                active = PrescriptionService.get_active_prescriptions(tenant_id, patient_id)
                                _send_dynamic_prescription_list(from_number, phone_number_id, active, "rx_view", "Active Prescriptions", "Select to view medicines.")
                            elif list_id == "rx_previous":
                                patient_id = "wa_" + "".join(filter(str.isdigit, from_number))
                                from app.services.prescription_service import PrescriptionService
                                prev = PrescriptionService.get_patient_prescriptions(tenant_id, patient_id)
                                _send_dynamic_prescription_list(from_number, phone_number_id, prev, "rx_view", "Previous Prescriptions", "Select to view past history.")
                            elif list_id == "rx_download":
                                patient_id = "wa_" + "".join(filter(str.isdigit, from_number))
                                from app.services.prescription_service import PrescriptionService
                                all_rx = PrescriptionService.get_patient_prescriptions(tenant_id, patient_id)
                                _send_dynamic_prescription_list(from_number, phone_number_id, all_rx, "rx_down", "Download Prescription", "Select to download PDF.")
                            elif list_id == "rx_schedule":
                                patient_id = "wa_" + "".join(filter(str.isdigit, from_number))
                                from app.services.prescription_service import PrescriptionService
                                sched = PrescriptionService.get_medicine_schedule(tenant_id, patient_id)
                                lines = ["⏰ *Today's Medicines*\n"]
                                for time_of_day, meds in sched.items():
                                    lines.append(f"*{time_of_day}*")
                                    if meds:
                                        for m in meds: lines.append(m)
                                    else:
                                        lines.append("No medicines")
                                    lines.append("")
                                send_whatsapp_message(from_number, "\n".join(lines).strip(), phone_number_id)
                            elif list_id == "rx_refill":
                                send_whatsapp_message(from_number, "💊 Refill request has been sent to the hospital pharmacy. They will contact you shortly.", phone_number_id)
                            elif list_id == "rx_ask_ai":
                                send_whatsapp_message(from_number, "🤖 Please type your question about your medicines (e.g., 'Can I take Telmisartan before food?').", phone_number_id)
                            elif list_id.startswith("rx_view_"):
                                rx_id = list_id.replace("rx_view_", "")
                                from app.services.prescription_service import PrescriptionService
                                rx = PrescriptionService.get_prescription(tenant_id, rx_id)
                                if rx:
                                    msg = PrescriptionService.format_prescription_for_whatsapp(rx)
                                    send_whatsapp_message(from_number, msg, phone_number_id)
                                else:
                                    send_whatsapp_message(from_number, "Prescription not found.", phone_number_id)
                            elif list_id.startswith("rx_down_"):
                                rx_id = list_id.replace("rx_down_", "")
                                from app.services.prescription_service import PrescriptionService
                                rx = PrescriptionService.get_prescription(tenant_id, rx_id)
                                if rx and rx.image_url:
                                    send_whatsapp_message(from_number, f"⬇️ Download your prescription here: {rx.image_url}", phone_number_id)
                                else:
                                    send_whatsapp_message(from_number, "Prescription document not available.", phone_number_id)
                            
                            # ── Existing Patient Profile Selection ──────────────────────
                            elif list_id.startswith("select_patient_"):
                                patient_id = list_id.replace("select_patient_", "")
                                from app.services.patient_service import PatientService
                                patient = PatientService.get_patient(tenant_id, patient_id)
                                if patient:
                                    patient_name = patient.name
                                    send_whatsapp_message(from_number, f"👤 Selected: *{patient_name}*\nLet's book an appointment!", phone_number_id)
                                    send_flow_cta_message(from_number, phone_number_id, patient_name)
                                else:
                                    send_whatsapp_message(from_number, "Profile not found. Please try again.", phone_number_id)
                                    send_patient_classification_message(from_number, phone_number_id)
                            elif list_id == "patient_new":
                                send_registration_flow_cta_message(from_number, phone_number_id, profile_name)

                        elif int_type == "button_reply":
                            button_id = interactive.get("button_reply", {}).get("id", "")
                            if button_id == "patient_existing":
                                # Look up existing profiles by phone number
                                from app.services.patient_service import PatientService
                                patients = PatientService.get_patients_by_phone(tenant_id, from_number)
                                if patients:
                                    send_existing_profiles_message(from_number, phone_number_id, patients, profile_name)
                                else:
                                    send_whatsapp_message(from_number, "No existing profiles found with your number. Let's register you as a new patient! 📋", phone_number_id)
                                    send_registration_flow_cta_message(from_number, phone_number_id, profile_name)
                            elif button_id == "patient_guest":
                                send_flow_cta_message(from_number, phone_number_id, profile_name)
                            elif button_id == "patient_new":
                                send_registration_flow_cta_message(from_number, phone_number_id, profile_name)
                            elif button_id == "report_timeline":
                                patient_id = "wa_" + "".join(filter(str.isdigit, from_number))
                                from app.services.report_service import ReportService
                                reports = ReportService.get_patient_reports(tenant_id, patient_id, limit=20)
                                timeline_text = ReportService.format_timeline_for_whatsapp(reports)
                                send_whatsapp_message(from_number, timeline_text, phone_number_id)
                            elif button_id in ("menu_book_appointment_direct",):
                                send_patient_classification_message(from_number, phone_number_id)
                            elif button_id == "menu_main":
                                send_main_menu_message(from_number, phone_number_id)

                        elif int_type == "nfm_reply":
                            response_json = interactive.get("nfm_reply", {}).get("response_json", "{}")
                            try:
                                import json
                                resp_data = json.loads(response_json)
                                status = resp_data.get("status")
                                doctor = resp_data.get("doctor", "Doctor")
                                
                                if status == "appointment_confirmed":
                                    send_success_messages(from_number, phone_number_id, doctor, tenant_id)
                                elif status == "registration_success":
                                    send_whatsapp_message(from_number, "✅ Registration Successful!", phone_number_id)
                                    send_patient_classification_message(from_number, phone_number_id)
                            except Exception as e:
                                logger.error(f"[nfm_reply] parse error: {e}")

                                
                    elif message_type in ("image", "document"):
                        # ── Medical Report Upload Flow ─────────────────────────────
                        media_obj = message.get(message_type, {})
                        media_id = media_obj.get("id", "")
                        mime_type = media_obj.get("mime_type", "image/jpeg")
                        caption = media_obj.get("caption", "").lower()
                        
                        # Check if user is in a report-upload context (caption hint or last msg state)
                        patient_id = "wa_" + "".join(filter(str.isdigit, from_number))
                        
                        if media_id:
                            send_whatsapp_message(from_number, "⏳ Processing your report...", phone_number_id)
                            import threading
                            threading.Thread(
                                target=_process_whatsapp_media_report,
                                args=(from_number, phone_number_id, media_id, mime_type, patient_id, tenant_id)
                            ).start()
                        else:
                            send_whatsapp_message(from_number, "❌ Could not receive the file. Please try again.", phone_number_id)
                            
                    elif message_type in ("audio", "video"):
                        send_whatsapp_message(from_number,
                            "📎 I received your file. Our team will review it shortly.", phone_number_id)
    except Exception as e:
        logger.exception(f"[process] Error: {e}")

# ── Webhook endpoints ─────────────────────────────────────────────────────────
@router.get("/webhook")
def verify_webhook(request: Request):
    mode      = request.query_params.get("hub.mode")
    token     = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode and token:
        if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
            logger.info("[webhook] Verified.")
            return Response(content=challenge, media_type="text/plain")
        raise HTTPException(status_code=403, detail="Verification failed")
    raise HTTPException(status_code=400, detail="Missing hub params")

@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
    except Exception:
        return Response(content="EVENT_RECEIVED", status_code=200)
    _debug_log(f"[webhook] object={body.get('object')} entries={len(body.get('entry', []))}")
    if body.get("object") == "whatsapp_business_account":
        background_tasks.add_task(process_whatsapp_message, body)
    return Response(content="EVENT_RECEIVED", status_code=200)

# ── Flow health / management endpoints ───────────────────────────────────────
@router.get("/flow/health")
async def flow_crypto_health():
    ring = get_keyring_status()
    ok   = ring.get("key_count", 0) > 0
    return {
        "status": "ok" if ok else "error",
        "private_key_path_exists": os.path.exists(PRIVATE_KEY_PATH),
        "public_key_path_exists":  os.path.exists(PUBLIC_KEY_PATH),
        **ring,
        "hint": (
            "Run `python sync_keys.py` to generate and upload keys." if not ok else
            "Keyring active. If 421 persists after running sync_keys.py, wait 5 min for Meta CDN."
        ),
    }

@router.post("/flow/rotate-keys")
async def flow_rotate_keys():
    invalidate_key_cache()
    ring = get_keyring_status()
    return {"status": "reloaded", **ring}

# ── Flow data endpoint ────────────────────────────────────────────────────────
@router.post("/flow")
async def whatsapp_flow_endpoint(request: Request):
    """
    WhatsApp Flows Data Endpoint.
    Handles both encrypted (production) and unencrypted (development) requests.
    """
    body = await request.json()

    enc_key_b64  = body.get("encrypted_aes_key", "")
    enc_flow_b64 = body.get("encrypted_flow_data", "")
    enc_iv_b64   = body.get("initial_vector", "")
    has_enc      = bool(enc_key_b64 and enc_flow_b64 and enc_iv_b64)

    # Decode flow token for autofill
    flow_token_val = body.get("flow_token", "")
    if not flow_token_val and has_enc:
        # In prod, it's inside decrypted_body, but we haven't decrypted yet.
        pass
        
    _debug_log(
        f"[flow] REQUEST has_enc={has_enc} "
        f"aes_len={len(enc_key_b64)} flow_len={len(enc_flow_b64)} iv_len={len(enc_iv_b64)}"
    )

    # If this is a standard WhatsApp webhook, delegate to the message handler
    if body.get("object") == "whatsapp_business_account":
        import asyncio
        await asyncio.to_thread(process_whatsapp_message, body)
        return Response(content="EVENT_RECEIVED", status_code=200)

    if has_enc:
        # Log decoded byte lengths for debugging
        def _safe_b64(v):
            v = v.replace("-", "+").replace("_", "/")
            v += "=" * ((-len(v)) % 4)
            return base64.b64decode(v)
        try:
            raw_aes  = _safe_b64(enc_key_b64)
            raw_flow = _safe_b64(enc_flow_b64)
            raw_iv   = _safe_b64(enc_iv_b64)
            _debug_log(f"[flow] DECODED aes={len(raw_aes)}B flow={len(raw_flow)}B iv={len(raw_iv)}B")
        except Exception as e:
            _debug_log(f"[flow] Base64 decode error: {e}")

        try:
            decrypted_body, aes_key, iv = decrypt_whatsapp_flow_request(
                enc_key_b64, enc_flow_b64, enc_iv_b64)
            action = decrypted_body.get("action")
            _debug_log(f"[flow] DECRYPTED action={action} screen={decrypted_body.get('screen')}")
        except FileNotFoundError as e:
            logger.error(f"[flow] Key missing: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except ValueError as e:
            logger.info(f"[flow] Client used old encryption key. Returning 421 to trigger automatic key rotation (this is normal behavior).")
            return Response(status_code=421, content="Decryption failed")
        except Exception as e:
            import traceback
            logger.error(f"[flow] Unexpected: {e}\n{traceback.format_exc()}")
            return Response(status_code=421, content=f"Decryption failed: {e}")
    else:
        decrypted_body = body
        action         = decrypted_body.get("action")
        aes_key, iv    = None, None

    screen = decrypted_body.get("screen")
    data   = decrypted_body.get("data", {})
    flow_token_val = decrypted_body.get("flow_token", "")
    
    phone_prefill, name_prefill = "", ""
    if flow_token_val and flow_token_val.startswith("tk_"):
        try:
            encoded_state = flow_token_val[3:]
            padding = len(encoded_state) % 4
            if padding:
                encoded_state += "=" * (4 - padding)
            state_json = base64.urlsafe_b64decode(encoded_state).decode()
            state = json.loads(state_json)
            phone_prefill = state.get("p", "")
            name_prefill = state.get("n", "")
            _debug_log(f"[flow] Extracted prefill: name='{name_prefill}', phone='{phone_prefill}'")
        except Exception as e:
            _debug_log(f"[flow] Failed to decode flow_token: {e}")

    # ── Flow State Machine ────────────────────────────────────────────────────
    response_data = None
    
    # Resolve tenant from the flow_token (which may encode tenant context)
    # or from the phone_number_id in the request body.
    _flow_phone_id = body.get("phone_number_id", "") or data.get("phone_number_id", "")
    from app.services.tenant_service import TenantService as _FlowTenantService
    _flow_tenant = _FlowTenantService.get_tenant_by_phone_number_id(_flow_phone_id) if _flow_phone_id else None
    tenant_id = _flow_tenant.id if _flow_tenant else settings.DEFAULT_TENANT_ID

    if action == "ping":
        response_data = {"version": "3.0", "data": {"status": "active"}}

    elif action == "INIT":
        flow_type = "clinic"
        if flow_token_val and flow_token_val.startswith("tk_"):
            try:
                encoded_state = flow_token_val[3:]
                padding = len(encoded_state) % 4
                if padding:
                    encoded_state += "=" * (4 - padding)
                state_json = base64.urlsafe_b64decode(encoded_state).decode()
                state = json.loads(state_json)
                flow_type = state.get("f", "clinic")
            except Exception:
                pass

        if flow_type == "register":
            response_data = {
                "version": "3.0", "screen": "PATIENT_REGISTRATION",
                "data": {
                    "patient_name_prefill": name_prefill,
                    "patient_phone_prefill": phone_prefill,
                },
            }
        else:
            doctors = DoctorService.get_all_doctors(tenant_id)
            specialties_set = set(doc.specialization for doc in doctors if doc.specialization)
            specialties = [{"id": s, "title": s} for s in sorted(specialties_set)]
            
            response_data = {
                "version": "3.0", "screen": "DOCTOR_SELECTION",
                "data": {
                    "specialties": specialties,
                    "doctors": [], "is_doctor_enabled": False,
                    "patient_name_prefill": name_prefill,
                    "patient_phone_prefill": phone_prefill,
                },
            }

    elif action == "data_exchange":
        trigger = data.get("trigger", "")

        if screen == "DOCTOR_SELECTION":
            if trigger == "specialty_selected":
                specialty = data.get("specialty", "")
                doctors = DoctorService.get_all_doctors(tenant_id)
                available = [{"id": d.id, "title": f"Dr. {d.name}"} for d in doctors if d.specialization == specialty]
                
                specialties_set = set(doc.specialization for doc in doctors if doc.specialization)
                specialties = [{"id": s, "title": s} for s in sorted(specialties_set)]

                response_data = {
                    "version": "3.0", "screen": "DOCTOR_SELECTION",
                    "data": {
                        "specialties": specialties,
                        "doctors": available, "is_doctor_enabled": bool(available),
                        "patient_name_prefill": name_prefill,
                        "patient_phone_prefill": phone_prefill,
                    },
                }
            elif trigger == "doctor_selected_continue":
                specialty = data.get("specialty", "")
                doctor    = data.get("doctor", "")
                
                today = date.today()
                # Only show dates that actually have slots for this doctor
                dates_list = []
                for i in range(30):  # look ahead 30 days to find at least some slots
                    candidate = today + timedelta(days=i)
                    try:
                        slots = ScheduleService.get_available_slots(tenant_id, doctor, candidate)
                    except Exception:
                        slots = []
                    if slots:
                        dates_list.append({
                            "id": candidate.isoformat(),
                            "title": candidate.strftime("%A, %b %-d")
                        })
                    if len(dates_list) >= 14:  # cap at 14 selectable dates
                        break
                
                # Fallback: if no configured slots at all, show next 14 days
                if not dates_list:
                    dates_list = [
                        {"id": (today + timedelta(days=i)).isoformat(), "title": (today + timedelta(days=i)).strftime("%A, %b %-d")}
                        for i in range(14)
                    ]
                
                response_data = {
                    "version": "3.0", "screen": "DATE_TIME_SELECTION",
                    "data": {
                        "dates": dates_list,
                        "times": [], "is_time_enabled": False,
                        "specialty": specialty, "doctor": doctor,
                        "patient_name_prefill": name_prefill,
                        "patient_phone_prefill": phone_prefill,
                    },
                }

        elif screen == "DATE_TIME_SELECTION":
            if trigger == "date_selected":
                date_sel  = data.get("date", "")
                specialty = data.get("specialty", "")
                doctor    = data.get("doctor", "")
                
                today = date.today()
                dates_list = [
                    {"id": (today + timedelta(days=i)).isoformat(), "title": (today + timedelta(days=i)).strftime("%A, %b %-d")}
                    for i in range(14)
                ]
                
                times_list = []
                try:
                    target_date = datetime.strptime(date_sel, "%Y-%m-%d").date()
                    slots = ScheduleService.get_available_slots(tenant_id, doctor, target_date)
                    for s in slots:
                        t_obj = datetime.strptime(s.start_time, "%H:%M")
                        times_list.append({"id": s.start_time, "title": t_obj.strftime("%I:%M %p")})
                except Exception as e:
                    logger.error(f"[flow] Error fetching slots: {e}")
                
                # Fallback: if still no times (no schedule configured), generate default 9am-5pm
                if not times_list:
                    logger.warning(f"[flow] No slots from schedule for doctor={doctor} on {date_sel}, using default grid")
                    from datetime import time as _time
                    start_h, end_h = 9, 17
                    for h in range(start_h, end_h):
                        for m in (0, 30):
                            t_str = f"{h:02d}:{m:02d}"
                            t_obj = datetime.strptime(t_str, "%H:%M")
                            times_list.append({"id": t_str, "title": t_obj.strftime("%I:%M %p")})

                response_data = {
                    "version": "3.0", "screen": "DATE_TIME_SELECTION",
                    "data": {
                        "dates": dates_list,
                        "times": times_list,
                        "is_time_enabled": bool(times_list),
                        "specialty": specialty, "doctor": doctor,
                        "patient_name_prefill": name_prefill,
                        "patient_phone_prefill": phone_prefill,
                    },
                }
            elif trigger == "appointment_summary":
                specialty = data.get("specialty", "")
                doctor_id = data.get("doctor", "")
                date_str  = data.get("date", "")
                time_str  = data.get("time", "")
                name      = data.get("name", "")
                phone     = data.get("phone", "")
                
                # Fetch doctor name for summary display
                doc_obj = DoctorService.get_doctor(tenant_id, doctor_id)
                doctor_name = doc_obj.name if doc_obj else doctor_id
                
                summary   = (f"\U0001fa7a Doctor: Dr. {doctor_name}\n"
                             f"\U0001f4c5 Date: {date_str} at {time_str}\n\n"
                             f"\U0001f464 Patient Name: {name}\n"
                             f"\U0001f4de Phone: {phone}")
                
                response_data = {
                    "version": "3.0", "screen": "SUMMARY",
                    "data": {
                        "summary_text": summary,
                        "specialty": specialty, "doctor": doctor_id,
                        "date": date_str, "time": time_str,
                        "name": name, "phone": phone, "email": "", "symptoms": "",
                    },
                }

        elif screen == "PATIENT_REGISTRATION":
            if trigger == "registration_review":
                name = data.get("name", "")
                phone = data.get("phone", "")
                email = data.get("email", "")
                gender = data.get("gender", "")
                dob = data.get("dob", "")
                
                summary = (f"👤 Name: {name}\n"
                           f"📞 Phone: {phone}\n"
                           f"🎂 DOB: {dob}\n"
                           f"⚕️ Gender: {gender}")
                
                response_data = {
                    "version": "3.0", "screen": "REGISTRATION_SUMMARY",
                    "data": {
                        "summary_text": summary,
                        "name": name,
                        "phone": phone,
                        "email": email,
                        "gender": gender,
                        "dob": dob,
                    },
                }
                
        elif screen == "REGISTRATION_SUMMARY":
            if trigger == "final_registration":
                patient_phone = data.get("phone", "")
                patient_name  = data.get("name", "")
                patient_email = data.get("email", "")
                patient_gender = data.get("gender", "")
                patient_dob = data.get("dob", "")
                
                patient_id = "wa_" + "".join(filter(str.isdigit, patient_phone or "unknown"))
                
                try:
                    from app.db.supabase import db as _db
                    now = datetime.utcnow()
                    _db.collection("tenants").document(tenant_id)\
                       .collection("patients").document(patient_id)\
                       .set({
                           "name": patient_name,
                           "mobile_number": patient_phone,
                           "email": patient_email or None,
                           "gender": patient_gender,
                           "dob": patient_dob,
                           "created_at": now,
                           "updated_at": now,
                       }, merge=True)
                    status_val = "registration_success"
                except Exception as e:
                    logger.error(f"[flow] Error registering patient: {e}")
                    status_val = "error"
                    
                response_data = {
                    "version": "3.0", "screen": "SUCCESS",
                    "data": {"extension_message_response": {"params": {
                        "flow_token": decrypted_body.get("flow_token", ""),
                        "status": status_val,
                    }}},
                }

        elif screen == "SUMMARY":
            if trigger == "proceed_to_payment":
                response_data = {
                    "version": "3.0", "screen": "PAYMENT",
                    "data": {
                        "specialty": data.get("specialty", ""), "doctor": data.get("doctor", ""),
                        "date": data.get("date", ""), "time": data.get("time", ""),
                        "name": data.get("name", ""), "phone": data.get("phone", ""),
                        "email": data.get("email", ""), "symptoms": data.get("symptoms", "")
                    }
                }
                
        elif screen == "PAYMENT":
            if trigger == "final_confirm":
                payment_method = data.get("payment_method", "cash")
                try:
                    date_obj     = datetime.strptime(data.get("date", ""), "%Y-%m-%d").date()
                    time_str     = data.get("time", "09:00")
                    patient_phone = data.get("phone", "")
                    patient_name  = data.get("name", "")

                    # Derive a stable patient_id from phone (strip non-digits)
                    patient_id = "wa_" + "".join(filter(str.isdigit, patient_phone or "unknown"))

                    # Calculate end time (30-minute slots)
                    t_obj     = datetime.strptime(time_str, "%H:%M")
                    end_obj   = t_obj + timedelta(minutes=30)
                    end_str   = end_obj.strftime("%H:%M")

                    appt_in = AppointmentCreate(
                        patient_id=patient_id,
                        doctor_id=data.get("doctor", ""),
                        appointment_date=date_obj,
                        appointment_time=time_str,
                        appointment_end=end_str,
                        reason_for_visit=data.get("symptoms", ""),
                        status=AppointmentStatus.CONFIRMED,
                    )
                    created = AppointmentService.create_appointment(tenant_id, appt_in)

                    # Also store the patient's display info as metadata on the appointment doc, and ensure the patient exists
                    if created:
                        try:
                            from app.db.supabase import db as _db
                            _db.collection("tenants").document(tenant_id)\
                               .collection("appointments").document(created.id)\
                               .update({
                                   "patient_name":  patient_name,
                                   "patient_phone": patient_phone,
                                   "patient_email": data.get("email", ""),
                               })
                               
                            # Use None instead of empty string for email to satisfy EmailStr
                            patient_email = data.get("email", "").strip() or None
                            now = datetime.utcnow()
                            _db.collection("tenants").document(tenant_id)\
                               .collection("patients").document(patient_id)\
                               .set({
                                   "name": patient_name,
                                   "mobile_number": patient_phone,
                                   "email": patient_email,
                                   "gender": "Unknown",
                                   "dob": "1970-01-01",
                                   "created_at": now,
                                   "updated_at": now,
                               }, merge=True)
                        except Exception:
                            pass  # non-critical

                    status_val = "appointment_confirmed"
                except Exception as e:
                    logger.error(f"[flow] Error creating appointment: {e}")
                    status_val = "error"
                    
                response_data = {
                    "version": "3.0", "screen": "SUCCESS",
                    "data": {"extension_message_response": {"params": {
                        "flow_token": decrypted_body.get("flow_token", ""),
                        "status": status_val,
                        "doctor": data.get("doctor", ""),
                    }}},
                }

    if response_data is None:
        response_data = {
            "version": "3.0", "screen": "SUCCESS",
            "data": {"extension_message_response": {"params": {"status": "error"}}},
        }

    # ── Encrypt response if we have an AES key ────────────────────────────────
    if aes_key and iv:
        try:
            encrypted = encrypt_whatsapp_flow_response(response_data, aes_key, iv)
            _debug_log(f"[flow] RESPONSE encrypted OK len={len(encrypted)}")
            return Response(content=encrypted, media_type="text/plain")
        except Exception as e:
            logger.error(f"[flow] Encrypt failed: {e}")
            raise HTTPException(status_code=500, detail="Encryption failed")

    # Development mode — base64 encode unencrypted response
    b64_resp = base64.b64encode(json.dumps(response_data).encode()).decode()
    return Response(content=b64_resp, media_type="text/plain")
