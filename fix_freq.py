from pathlib import Path
p = Path("app/services/prescription_service.py")
content = p.read_text()

# We need to replace the parsing logic in get_medicine_schedule
old_logic = """
                if "1-" in freq or "morning" in freq or "od" in freq or "bd" in freq or "tds" in freq or "am" in freq:
                    schedule["Morning (8:00 AM)"].append(f"✓ {med_name} ({instructions})")
                
                if "-1-" in freq or "afternoon" in freq or "tds" in freq:
                    schedule["Afternoon (1:00 PM)"].append(f"✓ {med_name} ({instructions})")
                    
                if "-1" in freq or "night" in freq or "bd" in freq or "tds" in freq or "pm" in freq or "hs" in freq:
                    schedule["Night (9:00 PM)"].append(f"✓ {med_name} ({instructions})")
"""

new_logic = """
                is_morning = any(x in freq for x in ["1-", "morning", "od", "bd", "tds", "am", "once", "twice", "thrice", "daily"])
                is_afternoon = any(x in freq for x in ["-1-", "afternoon", "tds", "thrice"])
                is_night = any(x in freq for x in ["-1", "night", "bd", "tds", "pm", "hs", "twice", "thrice", "nightly", "bedtime"])
                
                if is_morning:
                    schedule["Morning (8:00 AM)"].append(f"✓ {med_name} ({instructions})")
                if is_afternoon:
                    schedule["Afternoon (1:00 PM)"].append(f"✓ {med_name} ({instructions})")
                if is_night:
                    schedule["Night (9:00 PM)"].append(f"✓ {med_name} ({instructions})")
                
                # Fallback: if we didn't match anything, just put it in morning so they don't miss it
                if not is_morning and not is_afternoon and not is_night and freq:
                    schedule["Morning (8:00 AM)"].append(f"✓ {med_name} ({instructions}) [Freq: {freq}]")
"""

content = content.replace(old_logic, new_logic)
p.write_text(content)
