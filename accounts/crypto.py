import base64
import hashlib
from cryptography.fernet import Fernet
from django.conf import settings

def get_cipher():
    key = getattr(settings, "ENCRYPTION_KEY", "")
    if not key:
        secret = settings.SECRET_KEY.encode("utf-8")
        derived = hashlib.sha256(secret).digest()
        key = base64.urlsafe_b64encode(derived).decode("utf-8")
    elif len(key) != 44:
        derived = hashlib.sha256(key.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(derived).decode("utf-8")
    return Fernet(key.encode("utf-8"))

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
    except Exception:
        return ""
