import sys

def refactor_agent(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    out = []
    out.append("import logging\n")
    out.append("from typing import Dict, Any\n")
    out.append("import time, os, json, base64\n")
    out.append("import requests as _requests\n")
    out.append("from app.services.whatsapp.sender import WhatsAppSender\n")
    out.append("from app.schemas.whatsapp_account import WhatsAppAccount\n")
    out.append("from app.core.config import settings\n")
    out.append("\n")
    out.append("logger = logging.getLogger(__name__)\n")
    out.append("WA_API_VERSION = 'v20.0'\n")
    out.append("\n")
    
    in_class = False
    
    for i, line in enumerate(lines):
        # Remove old imports and constants at the top, we'll keep it simple: start copying from deduplication
        if "router = APIRouter()" in line:
            continue
        if "@router" in line:
            break # stop at webhooks
            
        # Replace tokens
        line = line.replace("settings.WHATSAPP_TOKEN", "self.sender.access_token")
        
        # We want to wrap everything in a class PatientAgent
        # So when we see a def, we add self to it.
        if line.startswith("def _is_duplicate") or line.startswith("def _debug_log") or line.startswith("_processed_message_ids") or line.startswith("_DEDUP_TTL"):
            out.append(line)
        elif line.startswith("def "):
            if not in_class:
                out.append("\nclass PatientAgent:\n")
                out.append("    def __init__(self, account: WhatsAppAccount, sender: WhatsAppSender):\n")
                out.append("        self.account = account\n")
                out.append("        self.sender = sender\n")
                out.append("        self.tenant_id = account.tenant_id\n\n")
                in_class = True
                
            # Replace def func(args) with def func(self, args)
            line = line.replace("def process_whatsapp_message(", "def process_message(self, ")
            if line.startswith("def "):
                parts = line.split("(", 1)
                new_line = "    " + parts[0] + "(self"
                if parts[1].strip() != "):":
                    new_line += ", " + parts[1]
                else:
                    new_line += "):" + parts[1][2:]
                out.append(new_line)
        elif line.startswith("async def "):
            break # Stop at async endpoints
        else:
            if in_class:
                if line.strip() == "":
                    out.append(line)
                else:
                    out.append("    " + line)
            else:
                # ignore top level imports and stuff we already handled
                if line.startswith("import ") or line.startswith("from ") or line.startswith("logger =") or line.startswith("WA_API_VERSION =") or line.startswith("_ROOT") or line.startswith("DEBUG_LOG ="):
                    continue
                out.append(line)

    # Now we need to fix all internal function calls inside the class to use self.
    # Like send_whatsapp_message(...) -> self.send_whatsapp_message(...)
    funcs_to_replace = [
        "send_whatsapp_message", "send_whatsapp_reaction", "send_flow_cta_message",
        "send_patient_classification_message", "send_existing_profiles_message",
        "send_registration_flow_cta_message", "send_main_menu_message", "send_success_messages",
        "_send_prescriptions_submenu", "_send_dynamic_prescription_list", "_send_reports_submenu",
        "_download_whatsapp_media", "_format_report_result_message", "_process_whatsapp_media_report",
        "_handle_medicine_qa"
    ]
    
    final_out = []
    for line in out:
        for f in funcs_to_replace:
            # simple replacement, could have issues if substring, but these are unique enough
            line = line.replace(f + "(", "self." + f + "(")
            line = line.replace("self.self.", "self.") # fix double self
        final_out.append(line)
        
    with open(filepath, 'w') as f:
        f.writelines(final_out)

if __name__ == "__main__":
    refactor_agent(sys.argv[1])
