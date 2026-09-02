from __future__ import annotations

import base64
import json
import os
from typing import Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


KeyMaterial = Union[str, bytes]


def derive_key(material: KeyMaterial) -> bytes:
    raw = material.encode("utf-8") if isinstance(material, str) else material
    return HKDF(algorithm=SHA256(), length=32, salt=None, info=b"geo-security-watermark").derive(raw)


def encrypt_text(text: str, material: KeyMaterial) -> str:
    nonce = os.urandom(12)
    ciphertext = AESGCM(derive_key(material)).encrypt(nonce, text.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_text(token: str, material: KeyMaterial) -> str:
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    if len(raw) < 13:
        raise ValueError("invalid watermark token")
    return AESGCM(derive_key(material)).decrypt(raw[:12], raw[12:], None).decode("utf-8")


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
