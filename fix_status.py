import re
from pathlib import Path

p = Path("app/services/prescription_service.py")
content = p.read_text()

# We need to change:
# if status_val not in ("Verified", "Approved", "Needs Verification"):
# to:
# if status_val.lower() not in ("verified", "approved", "needs verification", "needs_verification"):
content = content.replace(
    'if status_val not in ("Verified", "Approved", "Needs Verification"):',
    'if str(status_val).lower() not in ("verified", "approved", "needs verification", "needs_verification"):'
)

p.write_text(content)
