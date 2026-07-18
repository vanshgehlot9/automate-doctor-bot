import logging
import json
from fastapi import APIRouter, Request, Response, HTTPException, BackgroundTasks
from app.core.config import settings
from app.services.whatsapp.webhook import WhatsAppWebhookHandler
from app.services.whatsapp.config_service import WhatsAppConfigService
from app.services.whatsapp.flow_encryption import WhatsAppFlowEncryption

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Standard Meta Webhook Verification.
    Meta uses a single webhook URL per App, so we verify using a global token.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if token == settings.WHATSAPP_VERIFY_TOKEN:
            return Response(content=challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Invalid verify token")

@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Standard Meta Webhook Receiver.
    """
    body = await request.json()
    
    if body.get("object") == "whatsapp_business_account":
        # Process in background to quickly return 200 OK to Meta
        background_tasks.add_task(WhatsAppWebhookHandler.handle_message_webhook, body)
        return Response(content="EVENT_RECEIVED", status_code=200)
        
    return Response(status_code=404)

@router.post("/flow/{phone_number_id}")
async def whatsapp_flow_endpoint(phone_number_id: str, request: Request, background_tasks: BackgroundTasks):
    """
    WhatsApp Flows Data Endpoint per phone_number_id.
    Handles encrypted requests dynamically based on the bot configuration.
    """
    body = await request.json()

    # ── Unencrypted ping / health-check (Meta sends this to verify the endpoint) ──
    action_raw = body.get("action", "")
    version_raw = body.get("version", "")
    enc_key_b64  = body.get("encrypted_aes_key", "")
    enc_flow_b64 = body.get("encrypted_flow_data", "")
    enc_iv_b64   = body.get("initial_vector", "")
    has_enc      = bool(enc_key_b64 and enc_flow_b64 and enc_iv_b64)

    if action_raw == "ping" and not has_enc:
        logger.info(f"[flow] ✅ Health-check ping (version={version_raw}) for phone_number_id={phone_number_id}")
        return Response(
            content=json.dumps({"version": version_raw, "data": {"status": "active"}}),
            media_type="application/json",
            status_code=200,
        )

    # Look up the account dynamically to get keys
    account = WhatsAppConfigService.get_account_by_phone_number_id(phone_number_id)
    if not account:
        logger.error(f"[flow] No active account found for phone_number_id: {phone_number_id}")
        return Response(status_code=404, content="Account not configured")

    enc_key_b64  = body.get("encrypted_aes_key", "")
    enc_flow_b64 = body.get("encrypted_flow_data", "")
    enc_iv_b64   = body.get("initial_vector", "")
    has_enc      = bool(enc_key_b64 and enc_flow_b64 and enc_iv_b64)

    if has_enc:
        flow_crypto = WhatsAppFlowEncryption(account.private_key_path, account.public_key_path)
        try:
            decrypted_body, aes_key, iv = flow_crypto.decrypt_request(enc_key_b64, enc_flow_b64, enc_iv_b64)
            action = decrypted_body.get("action")
            logger.info(f"[flow] DECRYPTED action={action}")
            
            # TODO: Here you would route the flow action (e.g., 'data_exchange', 'ping')
            # to the corresponding Agent or Flow handler logic if required.
            # Currently just returning a successful ping stub.
            
            if action == "ping":
                response_data = {"data": {"status": "active"}}
                enc_response = flow_crypto.encrypt_response(response_data, aes_key, iv)
                return Response(content=enc_response, media_type="text/plain", status_code=200)
                
            # If not ping, delegate based on bot type
            # ...
            return Response(status_code=421, content="Flow action not handled")
            
        except ValueError as e:
            logger.warning(f"[flow] ❌ Decryption FAILED: {e}")
            return Response(status_code=421, content="Decryption failed")
        except Exception as e:
            logger.error(f"[flow] Unexpected: {e}", exc_info=True)
            return Response(status_code=421, content=f"Decryption failed: {e}")
    else:
        # Standard WhatsApp webhook delivered to the flow endpoint (fallback)
        if body.get("object") == "whatsapp_business_account":
            background_tasks.add_task(WhatsAppWebhookHandler.handle_message_webhook, body)
            return Response(content="EVENT_RECEIVED", status_code=200)
            
        return Response(status_code=421, content="Unencrypted flows not supported")
