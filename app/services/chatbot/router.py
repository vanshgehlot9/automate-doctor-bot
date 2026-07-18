import logging
from typing import Dict, Any
from app.schemas.whatsapp_account import WhatsAppAccount
from app.schemas.doctor import DoctorInDB
from app.services.whatsapp.sender import WhatsAppSender
from app.services.chatbot.patient_agent import PatientAgent
from app.services.chatbot.doctor_agent import DoctorAgent

logger = logging.getLogger(__name__)

class ChatbotRouter:
    @staticmethod
    def route_webhook(body: Dict[Any, Any], account: WhatsAppAccount):
        """Route an incoming webhook based on the account's bot_type."""
        sender = WhatsAppSender(access_token=account.access_token, phone_number_id=account.phone_number_id)
        
        bot_type = account.bot_type.lower()
        
        logger.info(f"[ChatbotRouter] Routing to {bot_type} bot for tenant {account.tenant_id}")
        
        try:
            if bot_type == "patient":
                agent = PatientAgent(account=account, sender=sender)
                agent.process_message(body)
            elif bot_type == "doctor":
                agent = DoctorAgent(account=account, sender=sender)
                agent.process_message(body)
            else:
                logger.error(f"Unknown bot type: {bot_type} for phone_number_id: {account.phone_number_id}")
        except Exception as e:
            logger.error(f"Error processing message in ChatbotRouter for bot {bot_type}: {e}", exc_info=True)

    @staticmethod
    def route_webhook_as_doctor(body: Dict[Any, Any], account: WhatsAppAccount, doctor: DoctorInDB):
        """
        Force-route a message to DoctorAgent even if the receiving account is patient-type.
        Used when the sender's number matches a registered doctor's whatsapp_number.
        """
        sender = WhatsAppSender(access_token=account.access_token, phone_number_id=account.phone_number_id)
        logger.info(f"[ChatbotRouter] Force-routing to DoctorAgent for doctor={doctor.name} tenant={doctor.tenant_id}")
        try:
            agent = DoctorAgent(account=account, sender=sender)
            agent.process_message(body)
        except Exception as e:
            logger.error(f"Error in DoctorAgent for doctor {doctor.name}: {e}", exc_info=True)
