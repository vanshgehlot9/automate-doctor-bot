from pathlib import Path
p = Path("app/services/scheduler_service.py")
content = p.read_text()
content = content.replace("p.phone_number", "p.mobile_number")
p.write_text(content)
