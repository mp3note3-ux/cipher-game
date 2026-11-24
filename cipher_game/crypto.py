"""Authenticated encryption helpers built on PyCA cryptography."""

from __future__ import annotations

import base64
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_SIZE_BYTES = 32
NONCE_SIZE_BYTES = 12


def generate_key() -> bytes:
    """Generate a random 256-bit AES key."""
    return AESGCM.generate_key(bit_length=256)


def key_to_text(key: bytes) -> str:
    if len(key) != KEY_SIZE_BYTES:
        raise ValueError("AES-256 keys must be exactly 32 bytes.")
    return base64.b64encode(key).decode("ascii")


def key_from_text(value: str) -> bytes:
    try:
        key = base64.b64decode(value.strip(), validate=True)
    except Exception as exc:
        raise ValueError("The key file is not valid Base64.") from exc
    if len(key) != KEY_SIZE_BYTES:
        raise ValueError("The key file must contain a 32-byte AES-256 key.")
    return key


def encrypt_bytes(key: bytes, plaintext: bytes, associated_data: bytes) -> tuple[bytes, bytes]:
    """Return a fresh 96-bit nonce and authenticated ciphertext + tag."""
    if len(key) != KEY_SIZE_BYTES:
        raise ValueError("AES-256 keys must be exactly 32 bytes.")
    nonce = secrets.token_bytes(NONCE_SIZE_BYTES)
    ciphertext_and_tag = AESGCM(key).encrypt(nonce, plaintext, associated_data)
    return nonce, ciphertext_and_tag


def decrypt_bytes(
    key: bytes,
    nonce: bytes,
    ciphertext_and_tag: bytes,
    associated_data: bytes,
) -> bytes:
    """Decrypt or raise InvalidTag if the key/data/authenticated metadata is wrong."""
    if len(key) != KEY_SIZE_BYTES:
        raise ValueError("AES-256 keys must be exactly 32 bytes.")
    if len(nonce) != NONCE_SIZE_BYTES:
        raise ValueError("AES-GCM nonces must be exactly 12 bytes.")
    return AESGCM(key).decrypt(nonce, ciphertext_and_tag, associated_data)
