from pathlib import Path
p = Path("app/services/scheduler_service.py")
content = p.read_text()
content = content.replace("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_TOKEN")
p.write_text(content)
