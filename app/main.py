import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.*")

from fastapi import FastAPI, Request, Response, BackgroundTasks
from app.api.v1.api import api_router
from app.core.config import settings
from app.services.whatsapp.config_service import WhatsAppConfigService
from app.services.whatsapp.flow_encryption import WhatsAppFlowEncryption
from app.services.whatsapp.webhook import WhatsAppWebhookHandler
from app.services.whatsapp.flow_handler import handle_flow_data_exchange
import logging, json

logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        from app.services.scheduler_service import scheduler_service
        scheduler_service.start()
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
    
    yield
    
    # Shutdown
    try:
        from app.services.scheduler_service import scheduler_service
        scheduler_service.stop()
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

from app.middleware import ExceptionLoggingMiddleware

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(ExceptionLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.post("/webhook/flow")
async def flow_alias(request: Request, background_tasks: BackgroundTasks):
    """
    Meta WhatsApp Flows Data Endpoint (legacy alias without phone_number_id in path).
    Meta sends health-check pings here; also receives flow data exchange events.
    We derive the phone_number_id from the configured default, or from DB if available.
    """
    try:
        body = await request.json()
    except Exception:
        return Response(status_code=400, content="Invalid JSON")

    logger.info(f"[flow_alias] body keys={list(body.keys())}")

    # ── Standard webhook passthrough (some Meta setups send events here) ──
    if body.get("object") == "whatsapp_business_account":
        background_tasks.add_task(WhatsAppWebhookHandler.handle_message_webhook, body)
        return Response(content="EVENT_RECEIVED", status_code=200)

    # ── Unencrypted ping / health-check ──
    action = body.get("action", "")
    version = body.get("version", "")
    if action == "ping":
        logger.info(f"[flow_alias] ✅ Health-check ping received (version={version}) — responding active")
        return Response(
            content=json.dumps({"version": version, "data": {"status": "active"}}),
            media_type="application/json",
            status_code=200,
        )

    # ── Encrypted flow exchange — need the phone_number_id to load the right key ──
    # Meta includes the phone_number_id in the encrypted payload's metadata, but
    # for the /webhook/flow (no-ID) route we fall back to the env-configured one.
    phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID

    # Try to load account and decrypt
    account = WhatsAppConfigService.get_account_by_phone_number_id(phone_number_id) if phone_number_id else None

    enc_key_b64  = body.get("encrypted_aes_key", "")
    enc_flow_b64 = body.get("encrypted_flow_data", "")
    enc_iv_b64   = body.get("initial_vector", "")
    has_enc      = bool(enc_key_b64 and enc_flow_b64 and enc_iv_b64)

    if not has_enc:
        logger.warning(f"[flow_alias] No encrypted fields and not a ping — returning 421")
        return Response(status_code=421, content="Unencrypted flows not supported")

    if not account:
        logger.error(f"[flow_alias] No account configured for phone_number_id={phone_number_id}")
        return Response(status_code=404, content="Account not configured")

    flow_crypto = WhatsAppFlowEncryption(account.private_key_path, account.public_key_path)
    try:
        decrypted_body, aes_key, iv = flow_crypto.decrypt_request(enc_key_b64, enc_flow_b64, enc_iv_b64)
        action = decrypted_body.get("action")
        logger.info(f"[flow_alias] DECRYPTED action={action}")

        if action == "ping":
            response_data = {"version": version, "data": {"status": "active"}}
            enc_response = flow_crypto.encrypt_response(response_data, aes_key, iv)
            return Response(content=enc_response, media_type="text/plain", status_code=200)

        # ── data_exchange: drive flow screens ─────────────────────────────
        if action == "data_exchange" or action == "INIT":
            response_data = handle_flow_data_exchange(decrypted_body, account.tenant_id)
            enc_response = flow_crypto.encrypt_response(response_data, aes_key, iv)
            return Response(content=enc_response, media_type="text/plain", status_code=200)

        logger.warning(f"[flow_alias] Unknown action={action!r} — returning 421")
        return Response(status_code=421, content=f"Unhandled flow action: {action}")

    except ValueError as e:
        logger.warning(f"[flow_alias] ❌ Decryption FAILED: {e}")
        return Response(status_code=421, content=f"Decryption failed: {e}")
    except Exception as e:
        logger.error(f"[flow_alias] Unexpected: {e}", exc_info=True)
        return Response(status_code=500, content=f"Internal error: {e}")


@app.get("/")
def root():
    return {"message": "Welcome to the Healthcare AI Operating System API"}
