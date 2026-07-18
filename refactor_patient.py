import re
with open('app/services/chatbot/patient_agent.py', 'r') as f:
    lines = f.readlines()

new_lines = []
new_lines.append("import threading\n")
new_lines.append("_ctx = threading.local()\n\n")

for line in lines:
    line = line.replace("settings.WHATSAPP_TOKEN", "_ctx.sender.access_token")
    if line.startswith("def process_whatsapp_message(body: Dict[Any, Any]):"):
        new_lines.append("class PatientAgent:\n")
        new_lines.append("    def __init__(self, account, sender):\n")
        new_lines.append("        self.account = account\n")
        new_lines.append("        self.sender = sender\n")
        new_lines.append("        self.tenant_id = account.tenant_id\n\n")
        new_lines.append("    def process_message(self, body: Dict[Any, Any]):\n")
        new_lines.append("        _ctx.sender = self.sender\n")
    elif line.startswith("router = APIRouter()"):
        continue
    elif line.startswith("@router"):
        continue
    elif line.startswith("async def webhook"):
        break  # We don't need the webhook endpoints anymore
    else:
        # If it's inside process_whatsapp_message, indent it? No, we just replaced the def line.
        # Wait, process_whatsapp_message was at indentation 0. If we just replace its def with `    def process_message...`, the rest of the body needs to be indented!
        pass
