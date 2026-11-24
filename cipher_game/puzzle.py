"""Create and solve CipherKeys puzzle envelopes."""

from __future__ import annotations

import base64
import json
from typing import Any

from .crypto import decrypt_bytes, encrypt_bytes
from .korean import hangul_to_2beolsik, keys_to_hangul
from .layouts import LAYOUTS, apply_layout_sequence, generate_layout_sequence, reverse_layout_sequence

VERSION = 1
ALGORITHM = "AES-256-GCM"
ENCODING = "BASE32"


def _manifest(envelope: dict[str, Any]) -> dict[str, Any]:
    manifest = {
        "version": envelope.get("version"),
        "algorithm": envelope.get("algorithm"),
        "encoding": envelope.get("encoding"),
        "layout_sequence": envelope.get("layout_sequence"),
    }
    if (
        manifest["version"] != VERSION
        or manifest["algorithm"] != ALGORITHM
        or manifest["encoding"] != ENCODING
    ):
        raise ValueError("Unsupported puzzle version or algorithm metadata.")
    sequence = manifest["layout_sequence"]
    if (
        not isinstance(sequence, list)
        or len(sequence) < 2
        or any(item not in LAYOUTS for item in sequence)
    ):
        raise ValueError("Invalid keyboard layout sequence.")
    return manifest


def _canonical_manifest(manifest: dict[str, Any]) -> bytes:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")


def create_puzzle(
    message: str,
    key: bytes,
    layout_sequence: list[str] | None = None,
) -> dict[str, Any]:
    """Encrypt a Korean message and wrap it in a reversible puzzle envelope."""
    keystrokes = hangul_to_2beolsik(message)
    sequence = layout_sequence if layout_sequence is not None else generate_layout_sequence()
    manifest = _manifest({
        "version": VERSION,
        "algorithm": ALGORITHM,
        "encoding": ENCODING,
        "layout_sequence": sequence,
    })
    aad = _canonical_manifest(manifest)
    nonce, ciphertext_and_tag = encrypt_bytes(key, keystrokes.encode("utf-8"), aad)

    encoded = base64.b32encode(ciphertext_and_tag).decode("ascii").rstrip("=").lower()
    puzzle_text = apply_layout_sequence(encoded, sequence)
    return {
        **manifest,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "puzzle_text": puzzle_text,
    }


def solve_puzzle(envelope: dict[str, Any], key: bytes) -> str:
    """Reverse puzzle layers, authenticate/decrypt, and return Hangul."""
    manifest = _manifest(envelope)
    puzzle_text = envelope.get("puzzle_text")
    nonce_text = envelope.get("nonce")
    if not isinstance(puzzle_text, str) or not isinstance(nonce_text, str):
        raise ValueError("Puzzle envelope is missing puzzle_text or nonce.")

    encoded = reverse_layout_sequence(puzzle_text, manifest["layout_sequence"])
    padded = encoded.upper() + "=" * ((8 - len(encoded) % 8) % 8)
    try:
        ciphertext_and_tag = base64.b32decode(padded, casefold=False)
        nonce = base64.b64decode(nonce_text, validate=True)
    except Exception as exc:
        raise ValueError("Puzzle text or nonce has an invalid encoding.") from exc

    plaintext = decrypt_bytes(key, nonce, ciphertext_and_tag, _canonical_manifest(manifest))
    try:
        keystrokes = plaintext.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Decrypted bytes are not valid UTF-8.") from exc
    return keys_to_hangul(keystrokes)
