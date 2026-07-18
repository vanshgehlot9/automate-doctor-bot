import requests as _requests
import logging
import time
import os
import json
import base64

logger = logging.getLogger(__name__)

WA_API_VERSION = "v20.0"
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
DEBUG_LOG = os.path.join(_ROOT, "whatsapp_debug.log")

def _debug_log(msg: str):
    logger.warning(msg)
    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

class WhatsAppSender:
    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        self.base_url = f"https://graph.facebook.com/{WA_API_VERSION}/{self.phone_number_id}/messages"

    def send_message(self, to_number: str, text: str) -> bool:
        if not self.access_token or not self.phone_number_id:
            logger.error("[send] Access token or phone_number_id missing.")
            return False
            
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": text, "preview_url": False},
        }
        try:
            resp = _requests.post(self.base_url, headers=self.headers, json=payload, timeout=10)
            _debug_log(f"[send] TO={to_number} STATUS={resp.status_code} BODY={resp.text[:200]}")
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"[send] Exception: {e}")
            return False

    def send_reaction(self, to_number: str, message_id: str, emoji: str):
        if not self.access_token or not self.phone_number_id:
            return
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "reaction",
            "reaction": {"message_id": message_id, "emoji": emoji}
        }
        try:
            _requests.post(self.base_url, headers=self.headers, json=payload, timeout=5)
        except Exception:
            pass

    def send_interactive_message(self, to_number: str, payload_data: dict) -> bool:
        """Generic method to send interactive payloads (buttons, lists, flows)"""
        if not self.access_token or not self.phone_number_id:
            return False
            
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            **payload_data
        }
        try:
            resp = _requests.post(self.base_url, headers=self.headers, json=payload, timeout=10)
            if resp.status_code != 200:
                logger.error(f"[send interactive] TO={to_number} STATUS={resp.status_code} BODY={resp.text[:500]}")
            else:
                _debug_log(f"[send interactive] TO={to_number} STATUS={resp.status_code}")
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"[send interactive] Exception: {e}")
            return False

    def upload_media(self, file_path: str, mime_type: str) -> str:
        """Upload a file to WhatsApp and return the media ID."""
        if not self.access_token or not self.phone_number_id:
            return ""
            
        url = f"https://graph.facebook.com/{WA_API_VERSION}/{self.phone_number_id}/media"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, mime_type)}
                data = {"messaging_product": "whatsapp"}
                resp = _requests.post(url, headers=headers, files=files, data=data, timeout=30)
                
            if resp.status_code == 200:
                result = resp.json()
                return result.get("id", "")
            else:
                logger.error(f"[upload media] Failed: {resp.status_code} {resp.text}")
                return ""
        except Exception as e:
            logger.error(f"[upload media] Exception: {e}")
            return ""

    def send_document(self, to_number: str, media_id: str, filename: str, caption: str = "") -> bool:
        """Send an uploaded document to the user."""
        if not self.access_token or not self.phone_number_id or not media_id:
            return False
            
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "document",
            "document": {
                "id": media_id,
                "filename": filename
            }
        }
        if caption:
            payload["document"]["caption"] = caption
        
        try:
            resp = _requests.post(self.base_url, headers=self.headers, json=payload, timeout=15)
            if resp.status_code != 200:
                logger.error(f"[send document] Failed: {resp.status_code} {resp.text[:500]}")
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"[send document] Exception: {e}")
            return False
