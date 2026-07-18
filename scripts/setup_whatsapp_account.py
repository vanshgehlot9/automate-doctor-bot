"""
One-time setup: Insert the patient WhatsApp account row into Supabase.
Run from the doctorbot directory:
  source venv/bin/activate
  python scripts/setup_whatsapp_account.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "1229036673621712")
DEFAULT_TENANT_ID = os.getenv("DEFAULT_TENANT_ID", "f0a1feb0-e39f-46c3-8795-ebbd0c265216")

db = create_client(SUPABASE_URL, SUPABASE_KEY)

# Absolute paths to keys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATIENT_PRIVATE_KEY = os.path.join(BASE_DIR, "keys", "patient", "private.pem")
PATIENT_PUBLIC_KEY  = os.path.join(BASE_DIR, "keys", "patient", "public.pem")

print(f"[setup] Using private key: {PATIENT_PRIVATE_KEY}")
print(f"[setup] Key exists: {os.path.exists(PATIENT_PRIVATE_KEY)}")

# Check if record already exists
existing = db.table("whatsapp_accounts").select("id").eq("phone_number_id", PHONE_NUMBER_ID).execute()
if existing.data:
    print(f"[setup] ✅ Account for phone_number_id={PHONE_NUMBER_ID} already exists (id={existing.data[0]['id']})")
    print("[setup] Updating private_key_path and access_token...")
    res = db.table("whatsapp_accounts").update({
        "access_token": WHATSAPP_TOKEN,
        "private_key_path": PATIENT_PRIVATE_KEY,
        "public_key_path": PATIENT_PUBLIC_KEY,
        "status": "active",
    }).eq("phone_number_id", PHONE_NUMBER_ID).execute()
    print(f"[setup] Updated: {res.data}")
else:
    print(f"[setup] Inserting new account for phone_number_id={PHONE_NUMBER_ID}...")
    res = db.table("whatsapp_accounts").insert({
        "tenant_id": DEFAULT_TENANT_ID,
        "bot_name": "Patient Bot",
        "bot_type": "patient",
        "phone_number": "+919000272057",
        "phone_number_id": PHONE_NUMBER_ID,
        "access_token": WHATSAPP_TOKEN,
        "private_key_path": PATIENT_PRIVATE_KEY,
        "public_key_path": PATIENT_PUBLIC_KEY,
        "verify_token": "12345",
        "status": "active",
    }).execute()
    if res.data:
        print(f"[setup] ✅ Account created: {res.data[0]['id']}")
    else:
        print(f"[setup] ❌ Insert failed: {res}")

# Verify lookup works
check = db.table("whatsapp_accounts").select("*").eq("phone_number_id", PHONE_NUMBER_ID).eq("status", "active").execute()
if check.data:
    row = check.data[0]
    print(f"\n[setup] ✅ Verification: account found in DB")
    print(f"  id={row['id']}")
    print(f"  bot_type={row['bot_type']}")
    print(f"  phone_number_id={row['phone_number_id']}")
    print(f"  private_key_path={row['private_key_path']}")
    print(f"  key file exists: {os.path.exists(row['private_key_path'])}")
else:
    print("[setup] ❌ Verification FAILED — account not found after insert!")
