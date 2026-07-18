import logging
from typing import Optional
from app.db.supabase import db
from app.schemas.whatsapp_account import WhatsAppAccount

logger = logging.getLogger(__name__)

class WhatsAppConfigService:
    @staticmethod
    def get_account_by_phone_number_id(phone_number_id: str) -> Optional[WhatsAppAccount]:
        """Fetch WhatsApp account configuration by phone_number_id from the database."""
        try:
            res = db.table("whatsapp_accounts").select("*").eq("phone_number_id", phone_number_id).eq("status", "active").execute()
            if res.data and len(res.data) > 0:
                return WhatsAppAccount(**res.data[0])
            logger.warning(f"No active WhatsApp account found for phone_number_id: {phone_number_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching WhatsApp account config for {phone_number_id}: {e}")
            return None
