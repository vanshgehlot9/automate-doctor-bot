import logging
from typing import Dict, Any
from app.services.whatsapp.config_service import WhatsAppConfigService
from app.services.chatbot.router import ChatbotRouter
from app.services.doctor_service import DoctorService

logger = logging.getLogger(__name__)

class WhatsAppWebhookHandler:
    @staticmethod
    def handle_message_webhook(body: Dict[Any, Any]):
        """Handles incoming standard WhatsApp webhooks and routes them to the correct agent."""
        if body.get("object") != "whatsapp_business_account":
            return False
            
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # Check for failed statuses
                if "statuses" in value:
                    for status in value["statuses"]:
                        if status.get("status") == "failed":
                            err = status.get("errors", [{}])[0]
                            logger.warning(f"[status] FAILED to deliver to {status.get('recipient_id')} | Error: {err.get('message')}")
                            
                # Process messages
                if "messages" not in value:
                    continue
                    
                phone_number_id = value.get("metadata", {}).get("phone_number_id")
                if not phone_number_id:
                    continue
                    
                # Strict Aatomate Block (from original logic)
                if phone_number_id == "1118908934647384":
                    logger.warning("Hard-blocked Aatomate message from being processed by Doctorbot.")
                    continue

                # Extract the sender's "from" number
                messages = value.get("messages", [])
                from_number = messages[0].get("from", "") if messages else ""

                # ── Doctor-first routing ──────────────────────────────────────────────
                # If the SENDER's number is registered as a doctor's whatsapp_number,
                # route to DoctorAgent regardless of which business number received it.
                if from_number:
                    doctor = DoctorService.get_doctor_by_whatsapp_number(from_number)
                    if doctor:
                        logger.info(f"[webhook] Sender {from_number} is Doctor '{doctor.name}' — routing to DoctorAgent")
                        # Look up the business account for sender/reply
                        account = WhatsAppConfigService.get_account_by_phone_number_id(phone_number_id)
                        if account:
                            ChatbotRouter.route_webhook_as_doctor(body, account, doctor)
                        else:
                            logger.warning(f"[webhook] No account for phone_number_id={phone_number_id} — cannot reply to doctor")
                        continue  # Skip patient routing for this message
                # ─────────────────────────────────────────────────────────────────────

                # Look up account configuration (determines patient vs doctor bot)
                account = WhatsAppConfigService.get_account_by_phone_number_id(phone_number_id)
                if not account:
                    logger.warning(f"[multi-bot] No account found for phone_number_id={phone_number_id}. Ignoring.")
                    continue
                    
                # Route to appropriate bot (patient by default for this account)
                ChatbotRouter.route_webhook(body, account)
                
        return True
