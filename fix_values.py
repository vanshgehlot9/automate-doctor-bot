import re
from pathlib import Path

def get_val_replacer(match):
    prefix = match.group(1)
    obj = match.group(2)
    return f"{prefix}getattr({obj}, 'value', {obj})"

for p in [Path("app/services/prescription_service.py"), Path("app/services/chatbot/patient_agent.py")]:
    content = p.read_text()
    # Find patterns like obj.field.value or med.duration.value
    # specifically look for \b([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\.value\b
    
    # Actually, we can just replace .value with a safe wrapper, but only for known fields.
    # Let's just use regex safely: match anything ending in .value (except for enums where we already check)
    
    # We will manually replace them to be safe.
