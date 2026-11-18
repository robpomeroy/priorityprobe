import base64
import logging

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings

logger = logging.getLogger(__name__)

HKDF_SALT = b"prioritysuite-llm-key-derivation-salt"
HKDF_INFO = b"prioritysuite-user-llm-config-encryption"


def _derive_fernet_key(secret_bytes: bytes) -> bytes:
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=HKDF_SALT,
        info=HKDF_INFO,
    )
    return base64.urlsafe_b64encode(hkdf.derive(secret_bytes))


def get_cipher() -> Fernet:
    raw_key = getattr(settings, "ENCRYPTION_KEY", "")
    if raw_key:
        key_bytes = raw_key.encode("utf-8") if isinstance(raw_key, str) else raw_key
        try:
            return Fernet(key_bytes)
        except (ValueError, TypeError):
            # Not a valid 32-byte urlsafe base64 key; derive a secure key using HKDF
            derived = _derive_fernet_key(key_bytes)
            return Fernet(derived)

    secret = settings.SECRET_KEY.encode("utf-8")
    derived = _derive_fernet_key(secret)
    return Fernet(derived)


def encrypt_value(value: str) -> str:
    if not value:
        return ""
    cipher = get_cipher()
    return cipher.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(encrypted_value: str) -> str:
    if not encrypted_value:
        return ""
    try:
        cipher = get_cipher()
        return cipher.decrypt(encrypted_value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.warning(
            "Decryption failed: InvalidToken encountered. Check ENCRYPTION_KEY or SECRET_KEY."
        )
        return ""
    except (ValueError, TypeError) as exc:
        logger.warning("Decryption failed due to invalid ciphertext: %s", exc)
        return ""
