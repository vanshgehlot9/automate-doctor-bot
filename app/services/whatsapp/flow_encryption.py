import os, json, hashlib, logging
from base64 import b64decode, b64encode
from typing import Tuple, Any, Dict, List, Optional

from cryptography.hazmat.primitives.asymmetric.padding import OAEP, MGF1
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import algorithms, Cipher, modes
from cryptography.hazmat.primitives.serialization import load_pem_private_key

logger = logging.getLogger(__name__)

class WhatsAppFlowEncryption:
    def __init__(self, private_key_path: str, public_key_path: str):
        self.private_key_path = private_key_path
        self.public_key_path = public_key_path
        self._keyring: List[Tuple[Any, str]] = []
        self._keyring_loaded = False

    def _fp(self, key_obj) -> str:
        der = key_obj.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        return hashlib.sha256(der).hexdigest()[:16]

    def _load_key(self, path: str):
        try:
            with open(path, "rb") as fh:
                return load_pem_private_key(fh.read(), password=None)
        except Exception as e:
            logger.warning(f"[crypto] Could not load key from {path}: {e}")
            return None

    def _build_keyring(self) -> List[Tuple[Any, str]]:
        ring: List[Tuple[Any, str]] = []
        
        if os.path.exists(self.private_key_path):
            k = self._load_key(self.private_key_path)
            if k:
                ring.append((k, self._fp(k)))
                logger.info(f"[crypto] Loaded current key from FILE fp={ring[-1][1]} path={self.private_key_path}")
                
        if not ring:
            logger.error(f"[crypto] ❌ NO KEYS LOADED from {self.private_key_path} — decryption will fail!")
            raise FileNotFoundError(f"No usable private key in {self.private_key_path!r}")
            
        logger.info(f"[crypto] Keyring ready — {len(ring)} key(s) available.")
        return ring

    def _get_keyring(self):
        if not self._keyring_loaded:
            self._keyring = self._build_keyring()
            self._keyring_loaded = True
        return self._keyring

    def invalidate_key_cache(self):
        self._keyring, self._keyring_loaded = [], False
        logger.info("[crypto] Key cache invalidated.")

    def _safe_b64decode(self, v: str) -> bytes:
        v = v.replace("-", "+").replace("_", "/")
        v += "=" * ((-len(v)) % 4)
        return b64decode(v)

    def _try_rsa_decrypt(self, key, ciphertext: bytes) -> Optional[bytes]:
        try:
            return key.decrypt(ciphertext,
                OAEP(mgf=MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
        except ValueError:
            return None

    def decrypt_request(self, encrypted_aes_key_b64: str, encrypted_flow_data_b64: str, initial_vector_b64: str) -> Tuple[Dict[str, Any], bytes, bytes]:
        try:
            enc_aes_key  = self._safe_b64decode(encrypted_aes_key_b64)
            enc_flow     = self._safe_b64decode(encrypted_flow_data_b64)
            iv           = self._safe_b64decode(initial_vector_b64)
        except Exception as exc:
            raise ValueError(f"Base64 decode failed: {exc}") from exc

        if len(enc_aes_key) != 256:
            raise ValueError(f"Stale cached request (AES key = {len(enc_aes_key)} bytes). Cannot be decrypted.")

        ring = self._get_keyring()
        aes_key, winning_fp = None, None
        for key_obj, fp in ring:
            result = self._try_rsa_decrypt(key_obj, enc_aes_key)
            if result is not None:
                aes_key, winning_fp = result, fp
                break

        if aes_key is None:
            raise ValueError(f"RSA decryption failed with all keys in the keyring.")

        if len(enc_flow) < 16:
            raise ValueError("Encrypted flow data too short.")
            
        ciphertext, gcm_tag = enc_flow[:-16], enc_flow[-16:]

        try:
            dec = Cipher(algorithms.AES(aes_key), modes.GCM(iv, gcm_tag)).decryptor()
            plaintext = dec.update(ciphertext) + dec.finalize()
        except Exception as exc:
            raise ValueError(f"AES-GCM decryption failed: {exc}") from exc

        try:
            body = json.loads(plaintext.decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"Decrypted payload is not valid JSON: {exc}") from exc

        return body, aes_key, iv

    def encrypt_response(self, response: Dict[str, Any], aes_key: bytes, iv: bytes) -> str:
        flipped_iv = bytes(b ^ 0xFF for b in iv)
        data       = json.dumps(response, separators=(",", ":")).encode("utf-8")
        enc = Cipher(algorithms.AES(aes_key), modes.GCM(flipped_iv)).encryptor()
        ct  = enc.update(data) + enc.finalize()
        return b64encode(ct + enc.tag).decode("utf-8")
