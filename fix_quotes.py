from pathlib import Path

p = Path("app/services/prescription_service.py")
content = p.read_text()

# We just need to replace `"value"` inside getattr with `'value'` everywhere.
content = content.replace('getattr(med.strength, "value", med.strength)', "getattr(med.strength, 'value', med.strength)")
content = content.replace('getattr(med.frequency, "value", med.frequency)', "getattr(med.frequency, 'value', med.frequency)")
content = content.replace('getattr(med.duration, "value", med.duration)', "getattr(med.duration, 'value', med.duration)")
content = content.replace('getattr(med.instructions, "value", med.instructions)', "getattr(med.instructions, 'value', med.instructions)")

p.write_text(content)
