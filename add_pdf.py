from pathlib import Path
import re

p = Path("app/services/chatbot/patient_agent.py")
content = p.read_text()

method_str = """
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
"""

# Append to the end of PatientAgent class. Wait, it's easier to just append before the end of file?
# PatientAgent is the only class in the file.
# But it might have other code at the end. Let's just put it at the very bottom, inside the class.
# We can search for the last method.
# `_handle_action_pdf` is at the very end of the class. 

if "_generate_prescription_pdf" not in content:
    content += method_str
    p.write_text(content)
