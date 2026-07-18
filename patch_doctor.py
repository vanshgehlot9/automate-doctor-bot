from pathlib import Path

p = Path("app/services/chatbot/doctor_agent.py")
content = p.read_text()

# 1. Modify process_message to handle images and documents
old_process_text = """        if msg_type == "text":
            text = msg.get("text", {}).get("body", "").strip()
            self._handle_text(from_number, session, doctor, text)"""

new_process_text = """        if msg_type == "text":
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
                self.sender.send_message(from_number, "❌ Could not receive the file. Please try again.")"""

content = content.replace(old_process_text, new_process_text)

# 2. Modify _show_labs to add upload prompt
old_show_labs = """    def _show_labs(self, from_number: str, session: dict, doctor):
        patient_id = session.get("selected_patient_id")
        patient_name = session.get("selected_patient_name", "Patient")
        if not patient_id:
            self.sender.send_message(from_number, "❌ No patient selected. Type *menu* to start over.")
            return
        tests = _get_lab_tests(self.tenant_id, patient_id)
        self.sender.send_message(from_number, _fmt_lab_tests(tests))
        # Re-show action menu
        self.sender.send_interactive_message(from_number, _patient_action_payload(patient_name))"""

new_show_labs = """    def _show_labs(self, from_number: str, session: dict, doctor):
        patient_id = session.get("selected_patient_id")
        patient_name = session.get("selected_patient_name", "Patient")
        if not patient_id:
            self.sender.send_message(from_number, "❌ No patient selected. Type *menu* to start over.")
            return
        tests = _get_lab_tests(self.tenant_id, patient_id)
        self.sender.send_message(from_number, _fmt_lab_tests(tests))
        self.sender.send_message(from_number, "📸 *To upload a new Lab Test or Report for this patient, simply send a Photo or PDF right now.*")
        # Re-show action menu
        self.sender.send_interactive_message(from_number, _patient_action_payload(patient_name))"""

content = content.replace(old_show_labs, new_show_labs)

# 3. Modify _show_reports to add upload prompt
old_show_reports = """    def _show_reports(self, from_number: str, session: dict, doctor):
        patient_id = session.get("selected_patient_id")
        patient_name = session.get("selected_patient_name", "Patient")
        if not patient_id:
            self.sender.send_message(from_number, "❌ No patient selected. Type *menu* to start over.")
            return
        reports = _get_reports(self.tenant_id, patient_id)
        self.sender.send_message(from_number, _fmt_reports(reports))
        self.sender.send_interactive_message(from_number, _patient_action_payload(patient_name))"""

new_show_reports = """    def _show_reports(self, from_number: str, session: dict, doctor):
        patient_id = session.get("selected_patient_id")
        patient_name = session.get("selected_patient_name", "Patient")
        if not patient_id:
            self.sender.send_message(from_number, "❌ No patient selected. Type *menu* to start over.")
            return
        reports = _get_reports(self.tenant_id, patient_id)
        self.sender.send_message(from_number, _fmt_reports(reports))
        self.sender.send_message(from_number, "📸 *To upload a new Lab Test or Report for this patient, simply send a Photo or PDF right now.*")
        self.sender.send_interactive_message(from_number, _patient_action_payload(patient_name))"""

content = content.replace(old_show_reports, new_show_reports)

# 4. Append methods
new_methods = """
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
"""

if "_download_whatsapp_media" not in content:
    content += new_methods

p.write_text(content)
print("Done patching.")
