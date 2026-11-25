"""Local-only Flask interface around the existing CipherKeys engine."""

from __future__ import annotations

from urllib.parse import urlsplit
from typing import Any

from flask import Flask, jsonify, render_template, request
from cryptography.exceptions import InvalidTag

from cipher_game import (
    create_puzzle,
    generate_key,
    key_from_text,
    key_to_text,
    solve_puzzle,
)
from cipher_game.korean import hangul_to_2beolsik
from cipher_game.layouts import generate_layout_sequence
from cipher_game.puzzle import detect_text_mode, KOREAN_MODE

MAX_MESSAGE_LENGTH = 20_000
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}


def _json_error(message: str, status: int):
    return jsonify({"ok": False, "error": message}), status


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create the local browser app.

    The web server is intended to run on loopback only. API mutations accept
    JSON requests only and reject foreign Origin headers. No CORS is enabled.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(
        MAX_CONTENT_LENGTH=1_000_000,
        JSON_AS_ASCII=False,
        TESTING=False,
    )
    if test_config:
        app.config.update(test_config)

    @app.before_request
    def restrict_local_access():
        host = request.host.split(":", 1)[0].strip("[]").lower()
        if host not in ALLOWED_HOSTS:
            return _json_error("CipherKeys only accepts local connections.", 403)

        if request.path.startswith("/api/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if request.mimetype != "application/json":
                return _json_error("API requests must use application/json.", 415)

            origin = request.headers.get("Origin")
            if origin:
                parsed = urlsplit(origin)
                if parsed.scheme != "http" or parsed.netloc.casefold() != request.host.casefold():
                    return _json_error("Cross-origin requests are not accepted.", 403)

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'"
        )
        if request.path.startswith("/api/") or request.path == "/":
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(413)
    def request_too_large(_error):
        return _json_error("The request is too large.", 413)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify({
            "ok": True,
            "application": "CipherKeys",
            "mode": "local-only",
            "algorithm": "AES-256-GCM",
        })

    @app.post("/api/encrypt")
    def encrypt():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return _json_error("Request body must be a JSON object.", 400)

        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            return _json_error("Enter a message before creating a puzzle.", 400)
        if len(message) > MAX_MESSAGE_LENGTH:
            return _json_error(f"Messages are limited to {MAX_MESSAGE_LENGTH:,} characters.", 400)

        transitions = payload.get("transitions", 3)
        if isinstance(transitions, bool) or not isinstance(transitions, int) or not 2 <= transitions <= 4:
            return _json_error("Keyboard transitions must be between 2 and 4.", 400)

        try:
            text_mode = detect_text_mode(message)
            layout_sequence = generate_layout_sequence(transitions)
            key = generate_key()
            envelope = create_puzzle(message, key, layout_sequence)
            route_label = (
                "Korean 2-beolsik"
                if text_mode == KOREAN_MODE
                else "UTF-8 (English, mixed, or other text)"
            )
            if text_mode == KOREAN_MODE:
                prepared_text = hangul_to_2beolsik(message)
                preparation_label = "Korean 2-beolsik conversion"
                preparation_preview = prepared_text
            else:
                prepared_text = message
                preparation_label = "UTF-8 preparation"
                preparation_preview = f"{len(prepared_text.encode('utf-8')):,} UTF-8 bytes"

            result = {
                "ok": True,
                "route": text_mode,
                "route_label": route_label,
                "envelope": envelope,
                # This key is returned only to this local browser response so
                # the user can download it separately. It is never persisted.
                "key": key_to_text(key),
                "steps": [
                    {"title": "Input detection", "detail": route_label},
                    {"title": preparation_label, "detail": preparation_preview},
                    {"title": "AES-256-GCM", "detail": "Authenticated encryption with a fresh 96-bit nonce"},
                    {"title": "Base32", "detail": "Ciphertext and authentication tag encoded as printable text"},
                    {"title": "Keyboard transformations", "detail": " → ".join(layout.upper() for layout in layout_sequence)},
                ],
            }
        except (TypeError, ValueError) as exc:
            return _json_error(str(exc), 400)

        return jsonify(result)

    @app.post("/api/decrypt")
    def decrypt():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return _json_error("Request body must be a JSON object.", 400)

        envelope = payload.get("envelope")
        key_text = payload.get("key")
        if not isinstance(envelope, dict):
            return _json_error("Choose a valid puzzle JSON file.", 400)
        if not isinstance(key_text, str) or not key_text.strip():
            return _json_error("Enter or select the matching secret key.", 400)

        try:
            key = key_from_text(key_text)
            message = solve_puzzle(envelope, key)
        except InvalidTag:
            return _json_error("Authentication failed. The key is incorrect or the puzzle was modified.", 400)
        except (TypeError, ValueError) as exc:
            return _json_error(str(exc), 400)

        return jsonify({"ok": True, "message": message})

    return app
