import logging
from typing import Dict, Any
import time, os, json, base64, uuid
import requests as _requests
from app.services.whatsapp.sender import WhatsAppSender
from app.schemas.whatsapp_account import WhatsAppAccount
from app.core.config import settings
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)
WA_API_VERSION = 'v20.0'
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
    logger.warning(msg)  # Forced to warning so Render logs it
    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

# ── WhatsApp send helpers ──────────────────────────────────────────────────────

class PatientAgent:
    def __init__(self, account: WhatsAppAccount, sender: WhatsAppSender):
        self.account = account
        self.sender = sender
        self.tenant_id = account.tenant_id

    def send_whatsapp_message(self, to_number: str, text: str, phone_number_id: str) -> bool:
        if not self.sender.access_token or not phone_number_id:
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
                headers={"Authorization": f"Bearer {self.sender.access_token}", "Content-Type": "application/json"},
                json=payload, timeout=10,
            )
            _debug_log(f"[send] TO={to_number} STATUS={resp.status_code} BODY={resp.text[:200]}")
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"[send] Exception: {e}")
            return False

    def send_whatsapp_reaction(self, to_number: str, message_id: str, emoji: str, phone_number_id: str):
        if not self.sender.access_token or not phone_number_id:
            return
        try:
            _requests.post(
                f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages",
                headers={"Authorization": f"Bearer {self.sender.access_token}", "Content-Type": "application/json"},
                json={"messaging_product": "whatsapp", "recipient_type": "individual",
                      "to": to_number, "type": "reaction",
                      "reaction": {"message_id": message_id, "emoji": emoji}},
                timeout=5,
            )
        except Exception:
            pass

    # ── WhatsApp Flow CTA Helper ────────────────────────────────────────────────────
    def send_flow_cta_message(self, to_number: str, phone_number_id: str, profile_name: str = "", patient_id: str = "", reschedule_id: str = "") -> bool:
        if not self.sender.access_token or not phone_number_id:
            logger.error("[send CTA] Missing token or phone_number_id")
            return False
        
        flow_id = os.environ.get("WHATSAPP_FLOW_ID", "1044794504647107")
    
        # Compact state payload serialized into URL-Safe Base64 flow_token
        state = {"p": to_number, "n": profile_name[:30], "f": "clinic", "id": patient_id, "rid": reschedule_id}
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
                headers={"Authorization": f"Bearer {self.sender.access_token}", "Content-Type": "application/json"},
                json=payload, timeout=10,
            )
            _debug_log(f"[send CTA] TO={to_number} STATUS={resp.status_code}")
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"[send CTA] Exception: {e}")
            return False

    def send_patient_classification_message(self, to_number: str, phone_number_id: str) -> bool:
        if not self.sender.access_token or not phone_number_id:
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
                        }
                    ]
                }
            }
        }
        url = f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages"
        try:
            resp = _requests.post(
                url,
                headers={"Authorization": f"Bearer {self.sender.access_token}", "Content-Type": "application/json"},
                json=payload, timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"[send classification] Exception: {e}")
            return False

    def send_existing_profiles_message(self, to_number: str, phone_number_id: str, patients: list, profile_name: str = "") -> bool:
        """Send a list of existing patient profiles found by phone number, plus 'Register New'."""
        if not self.sender.access_token or not phone_number_id:
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
                headers={"Authorization": f"Bearer {self.sender.access_token}", "Content-Type": "application/json"},
                json=payload, timeout=10,
            )
            _debug_log(f"[send profiles] TO={to_number} profiles={count} STATUS={resp.status_code}")
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"[send profiles] Exception: {e}")
            return False

    def send_registration_flow_cta_message(self, to_number: str, phone_number_id: str, profile_name: str = "") -> bool:
        if not self.sender.access_token or not phone_number_id:
            return False
        
        flow_id = os.environ.get("WHATSAPP_REGISTRATION_FLOW_ID", "1637200917949908")
    
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
                headers={"Authorization": f"Bearer {self.sender.access_token}", "Content-Type": "application/json"},
                json=payload, timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"[send CTA] Exception: {e}")
            return False

    def send_main_menu_message(self, to_number: str, phone_number_id: str) -> bool:
        if not self.sender.access_token or not phone_number_id:
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
                                {"id": "menu_lab_test", "title": "Lab Test"}
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
                headers={"Authorization": f"Bearer {self.sender.access_token}", "Content-Type": "application/json"},
                json=payload, timeout=10,
            )
            _debug_log(f"[send menu] TO={to_number} STATUS={resp.status_code}")
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"[send menu] Exception: {e}")
            return False

    def send_success_messages(self, to_number: str, phone_number_id: str, doctor_id: str, tenant_id: str, appt_id: str = ""):
        if not self.sender.access_token or not phone_number_id:
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
        headers = {"Authorization": f"Bearer {self.sender.access_token}", "Content-Type": "application/json"}
    
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
                                {"id": f"action_calendar::{appt_id}", "title": "Add to Calendar", "description": "Save to your schedule"},
                                {"id": f"action_pdf::{appt_id}", "title": "Download PDF", "description": "Get appointment receipt"},
                                {"id": f"action_reschedule::{appt_id}", "title": "Reschedule", "description": "Change date/time"},
                                {"id": f"action_cancel::{appt_id}", "title": "Cancel", "description": "Cancel appointment"}
                            ]
                        }
                    ]
                }
            }
        }
        _requests.post(url, headers=headers, json=list_payload)

    # ── Reports helpers ───────────────────────────────────────────────────────────

    def _send_prescriptions_submenu(self, to_number: str, phone_number_id: str):
        """Send the Prescriptions sub-menu as a list message."""
        if not self.sender.access_token or not phone_number_id:
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
            _requests.post(url, headers={"Authorization": f"Bearer {self.sender.access_token}", "Content-Type": "application/json"}, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"[prescriptions_submenu] {e}")


    def _send_dynamic_prescription_list(self, to_number: str, phone_number_id: str, prescriptions: list, action_prefix: str, header_text: str, body_text: str):
        """Dynamically generates a WhatsApp List message of prescriptions."""
        if not self.sender.access_token or not phone_number_id:
            return
        
        if not prescriptions:
            self.send_whatsapp_message(to_number, "No prescriptions found.", phone_number_id)
            return
        
        rows = []
        for i, p in enumerate(prescriptions[:10]): # Max 10 items in a section
            doc = str(getattr(p.doctor_name, "value", p.doctor_name)) if p.doctor_name else "Doctor"
            dt = str(getattr(p.prescription_date, "value", p.prescription_date)) if p.prescription_date else p.created_at.strftime("%d %b %Y")
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
            _requests.post(url, headers={"Authorization": f"Bearer {self.sender.access_token}", "Content-Type": "application/json"}, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"[dynamic_rx_list] {e}")


    def _send_reports_submenu(self, to_number: str, phone_number_id: str):
        """Send the Reports sub-menu as a list message."""
        if not self.sender.access_token or not phone_number_id:
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
                headers={"Authorization": f"Bearer {self.sender.access_token}", "Content-Type": "application/json"},
                json=payload, timeout=10,
            )
        except Exception as e:
            logger.error(f"[reports_submenu] {e}")


    def _download_whatsapp_media(self, media_id: str) -> tuple:
        """Download media bytes from WhatsApp Cloud API. Returns (bytes, mime_type)."""
        try:
            # Step 1: Get media URL
            meta_url = f"https://graph.facebook.com/{WA_API_VERSION}/{media_id}"
            meta_resp = _requests.get(
                meta_url,
                headers={"Authorization": f"Bearer {self.sender.access_token}"},
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
                headers={"Authorization": f"Bearer {self.sender.access_token}"},
                timeout=30,
            )
            if file_resp.status_code != 200:
                raise Exception(f"Media download failed: {file_resp.status_code}")
            return file_resp.content, mime_type
        except Exception as e:
            logger.error(f"[download_media] {e}")
            return None, None


    def _format_report_result_message(self, report) -> str:
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


    def _process_whatsapp_media_report(self, 
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
            image_bytes, actual_mime = self._download_whatsapp_media(media_id)
            if not image_bytes:
                self.send_whatsapp_message(to_number, "❌ Failed to download your file. Please try again.", phone_number_id)
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
                self.send_whatsapp_message(to_number, "⚠️ Report processed but AI extraction took longer than expected. Check 'My Reports' in a moment.", phone_number_id)
                return

            # Send the rich confirmation message
            msg = self._format_report_result_message(updated)
            self.send_whatsapp_message(to_number, msg, phone_number_id)

            # Follow-up interactive buttons
            url = f"https://graph.facebook.com/{WA_API_VERSION}/{phone_number_id}/messages"
            headers = {"Authorization": f"Bearer {self.sender.access_token}", "Content-Type": "application/json"}
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
            self.send_whatsapp_message(to_number, "❌ Something went wrong while processing your report. Please try again.", phone_number_id)


    def _handle_medicine_qa(self, patient_id: str, question: str, to_number: str, phone_number_id: str, tenant_id: str = None):
        """Answers patient questions using their active prescriptions and Gemini AI."""
        from app.services.prescription_service import PrescriptionService
        import google.generativeai as genai
        import os
        from app.core.config import settings as _settings
        _tid = tenant_id or _settings.DEFAULT_TENANT_ID
    
        active = PrescriptionService.get_active_prescriptions(_tid, patient_id)
        if not active:
            self.send_whatsapp_message(to_number, "I couldn't find any active prescriptions for you to answer this question. Please upload one first!", phone_number_id)
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
                self.send_whatsapp_message(to_number, "AI services are currently unavailable.", phone_number_id)
                return
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name="gemini-1.5-flash")
            response = model.generate_content(prompt)
            ai_reply = response.text.strip()
            self.send_whatsapp_message(to_number, "🤖 " + ai_reply, phone_number_id)
        except Exception as e:
            logger.error(f"[medicine_qa] AI Error: {e}")
            self.send_whatsapp_message(to_number, "❌ Sorry, I'm having trouble understanding right now. Please try again later.", phone_number_id)


    # ── Message processor ─────────────────────────────────────────────────────────
    def process_message(self, body: Dict[Any, Any]):
        try:
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if "statuses" in value:
                        for status in value["statuses"]:
                            if status.get("status") == "failed":
                                err = status.get("errors", [{}])[0]
                                logger.warning(f"[status] FAILED to deliver to {status.get('recipient_id')} | Error: {err.get('message')} ({err.get('code')}) | Details: {err.get('error_data', {}).get('details')}")
                        if "messages" not in value:
                            return
                    if "messages" not in value:
                        return
                    metadata        = value.get("metadata", {})
                    phone_number_id = metadata.get("phone_number_id", "")
                
                    # ── STRICT AATOMATE BLOCK ─────────────────────────────────────
                    # Absolutely prevent Doctorbot from processing messages meant for Aatomate
                    if phone_number_id == "1118908934647384":
                        logger.warning("Hard-blocked Aatomate message from being processed by Doctorbot.")
                        continue
                    # ─────────────────────────────────────────────────────────────
                
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
                    
                        # Ignore messages meant for Aatomate (or other bots)
                        if phone_number_id and phone_number_id != settings.WHATSAPP_PHONE_NUMBER_ID:
                            logger.info(f"Ignoring message meant for different bot (ID: {phone_number_id})")
                            continue
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
                            self.send_whatsapp_reaction(from_number, message_id, "\U0001f440", phone_number_id)
                        
                            greetings = {"hi", "hello", "hey", "help", "menu", "start", "hii", "helo"}
                            text_lower = text_body.lower()
                            is_greeting = any(text_lower.startswith(g) for g in greetings)
                            is_question = "?" in text_body or any(text_lower.startswith(q) for q in ["can ", "how ", "what ", "why ", "is ", "does ", "do ", "when ", "where ", "should ", "will ", "would "])
                        
                            if not is_greeting and len(text_lower) > 2:
                                if is_question:
                                    import threading
                                    patient_id = str(uuid.uuid5(uuid.NAMESPACE_OID, "wa_" + "".join(filter(str.isdigit, from_number))))
                                    threading.Thread(
                                        target=_handle_medicine_qa,
                                        args=(patient_id, text_body, from_number, phone_number_id, tenant_id)
                                    ).start()
                                else:
                                    patient_id = str(uuid.uuid5(uuid.NAMESPACE_OID, "wa_" + "".join(filter(str.isdigit, from_number))))
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
                                        self.send_whatsapp_message(from_number, "\n".join(lines), phone_number_id)
                                        self.send_whatsapp_reaction(from_number, message_id, "\u2705", phone_number_id)
                                    else:
                                        ok = self.send_main_menu_message(from_number, phone_number_id)
                                        if ok:
                                            self.send_whatsapp_reaction(from_number, message_id, "\u2705", phone_number_id)
                            else:
                                ok = self.send_main_menu_message(from_number, phone_number_id)
                                if ok:
                                    self.send_whatsapp_reaction(from_number, message_id, "\u2705", phone_number_id)
                            
                        elif message_type == "interactive":
                            interactive = message.get("interactive", {})
                            int_type = interactive.get("type", "")
                        
                            if int_type == "list_reply":
                                list_id = interactive.get("list_reply", {}).get("id", "")
                                if list_id == "menu_book_appointment":
                                    self.send_patient_classification_message(from_number, phone_number_id)
                                elif list_id == "menu_reports":
                                    self._send_reports_submenu(from_number, phone_number_id)
                                elif list_id == "menu_prescriptions":
                                    self._send_prescriptions_submenu(from_number, phone_number_id)
                                elif list_id == "menu_lab_test":
                                    self.send_whatsapp_message(from_number, "Lab testing services are coming soon.", phone_number_id)
                                elif list_id.startswith("action_calendar::"):
                                    appt_id = list_id.split("::")[1] if "::" in list_id else ""
                                    self._handle_action_calendar(from_number, phone_number_id, appt_id)
                                elif list_id.startswith("action_pdf::"):
                                    appt_id = list_id.split("::")[1] if "::" in list_id else ""
                                    self._handle_action_pdf(from_number, phone_number_id, appt_id)
                                elif list_id.startswith("action_reschedule::"):
                                    appt_id = list_id.split("::")[1] if "::" in list_id else ""
                                    self._handle_action_reschedule(from_number, phone_number_id, appt_id)
                                elif list_id.startswith("action_cancel::"):
                                    appt_id = list_id.split("::")[1] if "::" in list_id else ""
                                    self._handle_action_cancel(from_number, phone_number_id, appt_id)
                                elif list_id == "report_upload":
                                    self.send_whatsapp_message(from_number,
                                        "📸 Please send your report as a *photo* or *PDF document*. I'll analyse it with AI instantly!", phone_number_id)
                                elif list_id == "report_timeline":
                                    patient_id = str(uuid.uuid5(uuid.NAMESPACE_OID, "wa_" + "".join(filter(str.isdigit, from_number))))
                                    from app.services.report_service import ReportService
                                    reports = ReportService.get_patient_reports(tenant_id, patient_id, limit=20)
                                    timeline_text = ReportService.format_timeline_for_whatsapp(reports)
                                    self.send_whatsapp_message(from_number, timeline_text, phone_number_id)
                                elif list_id == "report_search":
                                    self.send_whatsapp_message(from_number,
                                        "🔍 Type the keyword to search your reports. Examples: *CBC*, *MRI*, *sugar*, *vitamin*", phone_number_id)
                            
                                # ── Prescriptions Handlers ─────────────────────────────────────
                                elif list_id in ("rx_active", "rx_previous", "rx_download", "rx_schedule"):
                                    from app.services.patient_service import PatientService
                                    patients = PatientService.get_patients_by_phone(tenant_id, from_number)
                                    pids = [p.id for p in patients] if patients else []
                                    fallback = str(uuid.uuid5(uuid.NAMESPACE_OID, "wa_" + "".join(filter(str.isdigit, from_number))))
                                    if fallback not in pids: pids.append(fallback)
                                    
                                    from app.services.prescription_service import PrescriptionService
                                    
                                    if list_id == "rx_active":
                                        active = []
                                        for pid in pids: active.extend(PrescriptionService.get_active_prescriptions(tenant_id, pid))
                                        # Sort by most recent
                                        active.sort(key=lambda x: x.created_at, reverse=True)
                                        self._send_dynamic_prescription_list(from_number, phone_number_id, active, "rx_view", "Active Prescriptions", "Select to view medicines.")
                                        
                                    elif list_id == "rx_previous":
                                        prev = []
                                        for pid in pids: prev.extend(PrescriptionService.get_patient_prescriptions(tenant_id, pid))
                                        prev.sort(key=lambda x: x.created_at, reverse=True)
                                        self._send_dynamic_prescription_list(from_number, phone_number_id, prev, "rx_view", "Previous Prescriptions", "Select to view past history.")
                                        
                                    elif list_id == "rx_download":
                                        all_rx = []
                                        for pid in pids: all_rx.extend(PrescriptionService.get_patient_prescriptions(tenant_id, pid))
                                        all_rx.sort(key=lambda x: x.created_at, reverse=True)
                                        self._send_dynamic_prescription_list(from_number, phone_number_id, all_rx, "rx_down", "Download Prescription", "Select to download PDF.")
                                        
                                    elif list_id == "rx_schedule":
                                        sched = {"Morning (8:00 AM)": [], "Afternoon (1:00 PM)": [], "Night (9:00 PM)": []}
                                        for pid in pids:
                                            s = PrescriptionService.get_medicine_schedule(tenant_id, pid)
                                            for k in sched: sched[k].extend(s.get(k, []))
                                            
                                        lines = ["⏰ *Today's Medicines*\n"]
                                        for time_of_day, meds in sched.items():
                                            lines.append(f"*{time_of_day}*")
                                            if meds:
                                                for m in meds: lines.append(m)
                                            else:
                                                lines.append("No medicines")
                                            lines.append("")
                                        self.send_whatsapp_message(from_number, "\n".join(lines).strip(), phone_number_id)
                                elif list_id.startswith("rx_view_"):
                                    rx_id = list_id.replace("rx_view_", "")
                                    from app.services.prescription_service import PrescriptionService
                                    rx = PrescriptionService.get_prescription(tenant_id, rx_id)
                                    if rx:
                                        msg = PrescriptionService.format_prescription_for_whatsapp(rx)
                                        self.send_whatsapp_message(from_number, msg, phone_number_id)
                                    else:
                                        self.send_whatsapp_message(from_number, "Prescription not found.", phone_number_id)
                                elif list_id.startswith("rx_down_"):
                                    rx_id = list_id.replace("rx_down_", "")
                                    from app.services.prescription_service import PrescriptionService
                                    rx = PrescriptionService.get_prescription(tenant_id, rx_id)
                                    if rx:
                                        if rx.image_url:
                                            self.send_whatsapp_message(from_number, f"⬇️ Download your original uploaded prescription here: {rx.image_url}", phone_number_id)
                                        else:
                                            self.send_whatsapp_message(from_number, "⏳ Generating your official prescription PDF...", phone_number_id)
                                            pdf_path = self._generate_prescription_pdf(rx)
                                            try:
                                                media_id = self.sender.upload_media(pdf_path, "application/pdf")
                                                if media_id:
                                                    self.sender.send_document(from_number, media_id, f"Prescription_{rx_id[:8]}.pdf", "📄 Here is your official digital prescription document. It is safe to tap and save to your device!")
                                                else:
                                                    self.send_whatsapp_message(from_number, "Failed to generate document.", phone_number_id)
                                            finally:
                                                import os
                                                if os.path.exists(pdf_path):
                                                    os.remove(pdf_path)
                                    else:
                                        self.send_whatsapp_message(from_number, "Prescription not found.", phone_number_id)
                            
                                # ── Existing Patient Profile Selection ──────────────────────
                                elif list_id.startswith("select_patient_"):
                                    patient_id = list_id.replace("select_patient_", "")
                                    from app.services.patient_service import PatientService
                                    patient = PatientService.get_patient(tenant_id, patient_id)
                                    if patient:
                                        patient_name = patient.name
                                        self.send_whatsapp_message(from_number, f"👤 Selected: *{patient_name}*\nLet's book an appointment!", phone_number_id)
                                        self.send_flow_cta_message(from_number, phone_number_id, patient_name, patient_id)
                                    else:
                                        self.send_whatsapp_message(from_number, "Profile not found. Please try again.", phone_number_id)
                                        self.send_patient_classification_message(from_number, phone_number_id)
                                elif list_id == "patient_new":
                                    self.send_registration_flow_cta_message(from_number, phone_number_id, profile_name)

                            elif int_type == "button_reply":
                                button_id = interactive.get("button_reply", {}).get("id", "")
                                if button_id == "patient_existing":
                                    # Look up existing profiles by phone number
                                    from app.services.patient_service import PatientService
                                    patients = PatientService.get_patients_by_phone(tenant_id, from_number)
                                    if patients:
                                        self.send_existing_profiles_message(from_number, phone_number_id, patients, profile_name)
                                    else:
                                        self.send_whatsapp_message(from_number, "No existing profiles found with your number. Let's register you as a new patient! 📋", phone_number_id)
                                        self.send_registration_flow_cta_message(from_number, phone_number_id, profile_name)
                                elif button_id == "patient_new":
                                    self.send_registration_flow_cta_message(from_number, phone_number_id, profile_name)
                                elif button_id == "water_drank":
                                    self.send_whatsapp_message(from_number, "Great job staying hydrated! 💧 Keep it up!", phone_number_id)
                                elif button_id == "chk_great":
                                    self.send_whatsapp_message(from_number, "That's wonderful to hear! 😊 Have a fantastic rest of your day!", phone_number_id)
                                elif button_id == "chk_okay":
                                    self.send_whatsapp_message(from_number, "Hope your day gets even better! Remember to take breaks. 💙", phone_number_id)
                                elif button_id == "chk_bad":
                                    self.send_whatsapp_message(from_number, "I'm sorry you're not feeling well. 🤕 Please get some rest, and don't hesitate to reach out to the clinic if you need medical assistance.", phone_number_id)
                                elif button_id == "report_timeline":
                                    patient_id = str(uuid.uuid5(uuid.NAMESPACE_OID, "wa_" + "".join(filter(str.isdigit, from_number))))
                                    from app.services.report_service import ReportService
                                    reports = ReportService.get_patient_reports(tenant_id, patient_id, limit=20)
                                    timeline_text = ReportService.format_timeline_for_whatsapp(reports)
                                    self.send_whatsapp_message(from_number, timeline_text, phone_number_id)
                                elif button_id in ("menu_book_appointment_direct",):
                                    self.send_patient_classification_message(from_number, phone_number_id)
                                elif button_id == "menu_main":
                                    self.send_main_menu_message(from_number, phone_number_id)

                            elif int_type == "nfm_reply":
                                response_json = interactive.get("nfm_reply", {}).get("response_json", "{}")
                                try:
                                    import json
                                    resp_data = json.loads(response_json)
                                    status = resp_data.get("status")
                                    doctor = resp_data.get("doctor", "Doctor")
                                
                                    if status == "appointment_confirmed":
                                        date_val = resp_data.get("date")
                                        time_val = resp_data.get("time")
                                        symptoms_val = resp_data.get("symptoms", "")
                                        
                                        # Decode patient_id from flow_token
                                        flow_token = resp_data.get("flow_token", "")
                                        patient_id_db = ""
                                        if flow_token.startswith("tk_"):
                                            try:
                                                import base64, json
                                                # Add padding back if needed
                                                b64_str = flow_token[3:]
                                                b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
                                                state = json.loads(base64.urlsafe_b64decode(b64_str).decode())
                                                patient_id_db = state.get("id", "")
                                                reschedule_id = state.get("rid", "")
                                            except Exception as e:
                                                logger.error(f"Failed to decode flow_token: {e}")
                                                reschedule_id = ""

                                        if not patient_id_db:
                                            # Fallback to UUID if missing
                                            patient_id_db = str(uuid.uuid5(uuid.NAMESPACE_OID, "wa_" + "".join(filter(str.isdigit, from_number))))
                                            
                                        try:
                                            from app.db.supabase import db
                                            if date_val and time_val and doctor:
                                                from datetime import datetime, timedelta
                                                
                                                time_str = time_val + ":00" if len(time_val) == 5 else time_val
                                                start_time_obj = datetime.strptime(time_str, "%H:%M:%S")
                                                end_time_obj = start_time_obj + timedelta(minutes=30)
                                                end_time_str = end_time_obj.strftime("%H:%M:%S")

                                                if reschedule_id:
                                                    db.table("appointments").update({
                                                        "doctor_id": doctor,
                                                        "appointment_date": date_val,
                                                        "appointment_time": time_str,
                                                        "appointment_end": end_time_str,
                                                        "reason_for_visit": symptoms_val,
                                                        "status": "scheduled"
                                                    }).eq("id", reschedule_id).execute()
                                                    appt_id = reschedule_id
                                                else:
                                                    res = db.table("appointments").insert({
                                                        "patient_id": patient_id_db,
                                                        "doctor_id": doctor,
                                                        "tenant_id": tenant_id,
                                                        "appointment_date": date_val,
                                                        "appointment_time": time_str,
                                                        "appointment_end": end_time_str,
                                                        "reason_for_visit": symptoms_val,
                                                        "status": "scheduled"
                                                    }).execute()
                                                    appt_id = res.data[0]['id'] if res.data else ""
                                                    
                                        except Exception as e:
                                            logger.error(f"[nfm_reply] DB insert/update error for appointment: {e}")
                                            appt_id = ""

                                        self.send_success_messages(from_number, phone_number_id, doctor, tenant_id, appt_id)
                                    elif status == "registration_success":
                                        self.send_whatsapp_message(from_number, "✅ Registration Successful!", phone_number_id)
                                        self.send_flow_cta_message(from_number, phone_number_id, profile_name)
                                except Exception as e:
                                    logger.error(f"[nfm_reply] parse error: {e}")

                                
                        elif message_type in ("image", "document"):
                            # ── Medical Report Upload Flow ─────────────────────────────
                            media_obj = message.get(message_type, {})
                            media_id = media_obj.get("id", "")
                            mime_type = media_obj.get("mime_type", "image/jpeg")
                            caption = media_obj.get("caption", "").lower()
                        
                            # Check if user is in a report-upload context (caption hint or last msg state)
                            patient_id = str(uuid.uuid5(uuid.NAMESPACE_OID, "wa_" + "".join(filter(str.isdigit, from_number))))
                        
                            if media_id:
                                self.send_whatsapp_message(from_number, "⏳ Processing your report...", phone_number_id)
                                import threading
                                threading.Thread(
                                    target=_process_whatsapp_media_report,
                                    args=(from_number, phone_number_id, media_id, mime_type, patient_id, tenant_id)
                                ).start()
                            else:
                                self.send_whatsapp_message(from_number, "❌ Could not receive the file. Please try again.", phone_number_id)
                            
                        elif message_type in ("audio", "video"):
                            self.send_whatsapp_message(from_number,
                                "📎 I received your file. Our team will review it shortly.", phone_number_id)
        except Exception as e:
            logger.exception(f"[process] Error: {e}")

    # ── Action Handlers ──────────────────────────────────────────────────────────

    def _handle_action_cancel(self, from_number: str, phone_number_id: str, appt_id: str):
        if not appt_id:
            self.send_whatsapp_message(from_number, "❌ Could not find the appointment to cancel.", phone_number_id)
            return
        from app.db.supabase import db
        try:
            db.table("appointments").update({"status": "cancelled"}).eq("id", appt_id).execute()
            self.send_whatsapp_message(from_number, "✅ Your appointment has been successfully cancelled.", phone_number_id)
        except Exception as e:
            logger.error(f"Error cancelling appt: {e}")
            self.send_whatsapp_message(from_number, "❌ Error cancelling appointment. Please try again later.", phone_number_id)

    def _handle_action_reschedule(self, from_number: str, phone_number_id: str, appt_id: str):
        if not appt_id:
            self.send_whatsapp_message(from_number, "❌ Could not find the appointment to reschedule.", phone_number_id)
            return
        
        # We need to re-trigger the flow but pass 'appt_id' as 'rid'
        from app.db.supabase import db
        import uuid
        try:
            res = db.table("appointments").select("patients(name)").eq("id", appt_id).execute()
            patient_name = res.data[0].get("patients", {}).get("name", "Patient") if res.data else "Patient"
            # Get patient ID
            patient_id = str(uuid.uuid5(uuid.NAMESPACE_OID, "wa_" + "".join(filter(str.isdigit, from_number))))
            
            self.send_whatsapp_message(from_number, "🔄 Let's reschedule your appointment.", phone_number_id)
            self.send_flow_cta_message(from_number, phone_number_id, profile_name=patient_name, patient_id=patient_id, reschedule_id=appt_id)
        except Exception as e:
            logger.error(f"Error rescheduling appt: {e}")

    def _handle_action_calendar(self, from_number: str, phone_number_id: str, appt_id: str):
        if not appt_id:
            return
        from app.db.supabase import db
        from datetime import datetime
        import requests
        try:
            res = db.table("appointments").select("*, doctors(name)").eq("id", appt_id).execute()
            if not res.data: return
            appt = res.data[0]
            
            dt_start_str = f"{appt.get('appointment_date')} {appt.get('appointment_time')}"
            dt_start_local = datetime.strptime(dt_start_str, "%Y-%m-%d %H:%M:%S")
            
            doctor_name = appt.get("doctors", {}).get("name") or "Doctor"
            
            nice_date = dt_start_local.strftime("%d %b %Y")
            nice_time = dt_start_local.strftime("%I:%M %p")
            
            # Dynamically fetch the current ngrok url or use fallback
            try:
                resp = requests.get("http://localhost:4040/api/tunnels", timeout=2)
                base_url = resp.json()["tunnels"][0]["public_url"]
            except:
                base_url = "https://swerve-buddhist-swaddling.ngrok-free.dev"
                
            ics_link = f"{base_url}/api/v1/appointments/{appt_id}/calendar.ics"
            
            msg = (
                "📅 *Add to Calendar*\n\n"
                f"*Dr. {doctor_name}*\n"
                f"🗓 Date: {nice_date}\n"
                f"⏰ Time: {nice_time}\n\n"
                "_Tap the native link below to instantly open your calendar app and save your appointment!_\n\n"
                f"👉 {ics_link}"
            )
            
            self.send_whatsapp_message(from_number, msg, phone_number_id)
        except Exception as e:
            logger.error(f"Error generating Calendar text: {e}")

    def _handle_action_pdf(self, to_number: str, phone_number_id: str, appt_id: str):
        from app.db.supabase import db
        from datetime import datetime
        try:
            res = db.table("appointments").select("*, doctors(name), patients(name)").eq("id", appt_id).execute()
            if not res.data:
                return
            appt = res.data[0]
            doc_name = appt.get("doctors", {}).get("name", "Doctor")
            pat_name = appt.get("patients", {}).get("name", "Patient")
            tm = appt.get("appointment_time", "")
            reason = appt.get("reason_for_visit", "Checkup")
            
            try:
                dt_obj = datetime.strptime(f"{dt} {tm}", "%Y-%m-%d %H:%M:%S")
                nice_date = dt_obj.strftime("%d %b %Y")
                nice_time = dt_obj.strftime("%I:%M %p")
            except:
                nice_date = dt
                nice_time = tm
            
            msg = (
                "📄 *Appointment Receipt*\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                f"*Patient:* {pat_name}\n"
                f"*Doctor:* Dr. {doc_name}\n"
                f"*Date:* {nice_date}\n"
                f"*Time:* {nice_time}\n"
                f"*Reason:* {reason}\n"
                f"*Status:* Confirmed\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "_Thank you for choosing Aatomate!_"
            )
            
            self.send_whatsapp_message(from_number, msg, phone_number_id)
        except Exception as e:
            logger.error(f"Error generating text receipt: {e}")

    def _generate_prescription_pdf(self, rx) -> str:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import tempfile, os
        
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        
        c = canvas.Canvas(path, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 24)
        c.drawString(50, height - 50, "Medical Prescription")
        
        c.setFont("Helvetica", 12)
        doc_name = str(getattr(rx.doctor_name, 'value', rx.doctor_name)) if rx.doctor_name else "Doctor"
        date_val = str(getattr(rx.prescription_date, 'value', rx.prescription_date)) if rx.prescription_date else getattr(rx, 'created_at', "Unknown Date")
        if hasattr(date_val, 'strftime'):
            date_val = date_val.strftime("%d %b %Y")
        
        c.drawString(50, height - 80, f"Doctor: Dr. {doc_name}")
        c.drawString(50, height - 100, f"Date: {date_val}")
        
        c.line(50, height - 110, width - 50, height - 110)
        
        y = height - 140
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "Medicines prescribed:")
        y -= 25
        
        c.setFont("Helvetica", 12)
        for med in rx.medicines:
            name = str(getattr(med.medicine_name, "value", med.medicine_name)) if med.medicine_name else "Unknown"
            strength = str(getattr(med.strength, "value", med.strength)) if med.strength else ""
            freq = str(getattr(med.frequency, "value", med.frequency)) if med.frequency else ""
            dur = str(getattr(med.duration, "value", med.duration)) if med.duration else ""
            inst = str(getattr(med.instructions, "value", med.instructions)) if med.instructions else ""
            
            line = f"• {name} {strength}"
            if freq: line += f" - {freq}"
            if dur: line += f" for {dur}"
            c.drawString(60, y, line)
            y -= 20
            if inst:
                c.setFont("Helvetica-Oblique", 10)
                c.drawString(80, y, f"Note: {inst}")
                c.setFont("Helvetica", 12)
                y -= 20
                
            if y < 100:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 12)
                
        c.save()
        return path

    # ── Webhook endpoints ─────────────────────────────────────────────────────────
