"""Create and solve CipherKeys puzzle envelopes."""

from __future__ import annotations

import base64
import json
from typing import Any

from .crypto import decrypt_bytes, encrypt_bytes
from .korean import hangul_to_2beolsik, keys_to_hangul
from .layouts import LAYOUTS, apply_layout_sequence, generate_layout_sequence, reverse_layout_sequence

VERSION = 2
LEGACY_VERSION = 1
ALGORITHM = "AES-256-GCM"
ENCODING = "BASE32"
KOREAN_MODE = "korean-2beolsik"
UTF8_MODE = "utf-8"


def detect_text_mode(message: str) -> str:
    """Select the Korean keyboard route for Hangul-only text; otherwise use UTF-8.

    Korean mode currently accepts precomposed Hangul syllables and ordinary
    spaces. English, punctuation, emoji, other scripts, and mixed-language
    messages use UTF-8 directly so that no characters are lost.
    """
    if not isinstance(message, str):
        raise TypeError("message must be a string")

    has_hangul = any("\uac00" <= char <= "\ud7a3" for char in message)
    hangul_or_spaces_only = all(
        char == " " or "\uac00" <= char <= "\ud7a3"
        for char in message
    )
    if message and has_hangul and hangul_or_spaces_only:
        return KOREAN_MODE
    return UTF8_MODE


def _manifest(envelope: dict[str, Any]) -> dict[str, Any]:
    version = envelope.get("version")
    if version not in (LEGACY_VERSION, VERSION):
        raise ValueError("Unsupported puzzle version.")

    manifest = {
        "version": version,
        "algorithm": envelope.get("algorithm"),
        "encoding": envelope.get("encoding"),
        "layout_sequence": envelope.get("layout_sequence"),
    }
    if manifest["algorithm"] != ALGORITHM or manifest["encoding"] != ENCODING:
        raise ValueError("Unsupported puzzle algorithm or encoding metadata.")

    sequence = manifest["layout_sequence"]
    if (
        not isinstance(sequence, list)
        or len(sequence) < 2
        or any(not isinstance(item, str) or item not in LAYOUTS for item in sequence)
    ):
        raise ValueError("Invalid keyboard layout sequence.")

    # Version 1 puzzles predate automatic route detection and always contain
    # Korean 2-beolsik keystrokes. Keep them decryptable.
    if version == VERSION:
        text_mode = envelope.get("text_mode")
        if text_mode not in (KOREAN_MODE, UTF8_MODE):
            raise ValueError("Unsupported or missing text mode metadata.")
        manifest["text_mode"] = text_mode

    return manifest


def _canonical_manifest(manifest: dict[str, Any]) -> bytes:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")


def create_puzzle(
    message: str,
    key: bytes,
    layout_sequence: list[str] | None = None,
) -> dict[str, Any]:
    """Automatically select a text route, encrypt it, and wrap it as a puzzle."""
    text_mode = detect_text_mode(message)
    if text_mode == KOREAN_MODE:
        prepared_text = hangul_to_2beolsik(message)
    else:
        prepared_text = message

    sequence = layout_sequence if layout_sequence is not None else generate_layout_sequence()
    manifest = _manifest({
        "version": VERSION,
        "algorithm": ALGORITHM,
        "encoding": ENCODING,
        "text_mode": text_mode,
        "layout_sequence": sequence,
    })
    aad = _canonical_manifest(manifest)
    nonce, ciphertext_and_tag = encrypt_bytes(
        key,
        prepared_text.encode("utf-8"),
        aad,
    )

    encoded = base64.b32encode(ciphertext_and_tag).decode("ascii").rstrip("=").lower()
    puzzle_text = apply_layout_sequence(encoded, sequence)
    return {
        **manifest,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "puzzle_text": puzzle_text,
    }


def solve_puzzle(envelope: dict[str, Any], key: bytes) -> str:
    """Reverse puzzle layers, authenticate/decrypt, and recover the source text."""
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

    plaintext = decrypt_bytes(
        key,
        nonce,
        ciphertext_and_tag,
        _canonical_manifest(manifest),
    )
    try:
        prepared_text = plaintext.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Decrypted bytes are not valid UTF-8.") from exc

    # Version 1 used Korean mode implicitly; version 2 records it explicitly.
    text_mode = manifest.get("text_mode", KOREAN_MODE)
    if text_mode == KOREAN_MODE:
        return keys_to_hangul(prepared_text)
    return prepared_text
