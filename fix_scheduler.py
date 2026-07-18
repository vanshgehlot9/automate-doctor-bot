from pathlib import Path
p = Path("app/services/scheduler_service.py")
content = p.read_text()
content = content.replace(
    "self.sender = WhatsAppSender()", 
    "from app.core.config import settings\n        self.sender = WhatsAppSender(settings.WHATSAPP_ACCESS_TOKEN, settings.WHATSAPP_PHONE_NUMBER_ID)"
)
p.write_text(content)
