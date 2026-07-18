from app.db.supabase import db
import json

res = db.table("prescriptions").select("id, medicines").execute()
for r in res.data:
    print(r["id"])
    print(json.dumps(r["medicines"], indent=2))
