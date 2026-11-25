import unittest

import cipher_game
from cipher_game.puzzle import MAX_MESSAGE_LENGTH, VERSION
from webapp.app import create_app


class CipherKeysWebAppTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()

    def encrypt(self, message="CipherKeys", transitions=2):
        return self.client.post("/api/encrypt", json={"message": message, "transitions": transitions})

    # --- pages and health -------------------------------------------------

    def test_home_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"CipherKeys", response.data)
        self.assertIn(b"Encryption explorer", response.data)

    def test_home_page_shows_application_version(self):
        response = self.client.get("/")
        self.assertIn(f"v{cipher_game.__version__}".encode(), response.data)

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["mode"], "local-only")
        self.assertEqual(body["version"], cipher_game.__version__)
        self.assertEqual(body["puzzle_format"], VERSION)

    # --- round trips --------------------------------------------------------

    def test_korean_round_trip(self):
        encrypted = self.encrypt("안녕")
        self.assertEqual(encrypted.status_code, 200)
        payload = encrypted.get_json()
        self.assertEqual(payload["route"], "korean-2beolsik")

        decrypted = self.client.post(
            "/api/decrypt",
            json={"envelope": payload["envelope"], "key": payload["key"]},
        )
        self.assertEqual(decrypted.status_code, 200)
        self.assertEqual(decrypted.get_json()["message"], "안녕")

    def test_english_and_mixed_round_trip(self):
        for message in ("Hello, World!", "안녕 Hello! 🌏"):
            with self.subTest(message=message):
                encrypted = self.encrypt(message, 3)
                self.assertEqual(encrypted.status_code, 200)
                payload = encrypted.get_json()
                self.assertEqual(payload["route"], "utf-8")
                decrypted = self.client.post(
                    "/api/decrypt",
                    json={"envelope": payload["envelope"], "key": payload["key"]},
                )
                self.assertEqual(decrypted.status_code, 200)
                self.assertEqual(decrypted.get_json()["message"], message)

    def test_non_ascii_json_is_not_escaped(self):
        response = self.encrypt("안녕")
        self.assertIn("Korean 2-beolsik".encode(), response.data)
        decrypt = self.client.post(
            "/api/decrypt",
            json={"envelope": response.get_json()["envelope"], "key": response.get_json()["key"]},
        )
        self.assertIn("안녕".encode("utf-8"), decrypt.data)

    def test_maximum_length_message_is_accepted(self):
        self.assertEqual(self.encrypt("a" * MAX_MESSAGE_LENGTH).status_code, 200)

    # --- authentication failures -------------------------------------------

    def test_wrong_key_fails_authentication(self):
        encrypted = self.encrypt().get_json()
        wrong_key = "A" * 43 + "="
        response = self.client.post(
            "/api/decrypt",
            json={"envelope": encrypted["envelope"], "key": wrong_key},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Authentication failed", response.get_json()["error"])

    def test_tampered_envelope_fails_authentication(self):
        encrypted = self.encrypt("Hello").get_json()
        envelope = dict(encrypted["envelope"])
        envelope["text_mode"] = "korean-2beolsik"
        response = self.client.post("/api/decrypt", json={"envelope": envelope, "key": encrypted["key"]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Authentication failed", response.get_json()["error"])

    def test_overlong_layout_sequence_is_rejected(self):
        encrypted = self.encrypt("Hello").get_json()
        envelope = dict(encrypted["envelope"])
        envelope["layout_sequence"] = ["qwerty", "dvorak"] * 50
        response = self.client.post("/api/decrypt", json={"envelope": envelope, "key": encrypted["key"]})
        self.assertEqual(response.status_code, 400)

    # --- input validation ---------------------------------------------------

    def test_invalid_transition_count_is_rejected(self):
        for bad in (9, 1, 5, 0, -1, True, False, 2.5, "3", None):
            with self.subTest(transitions=bad):
                response = self.client.post(
                    "/api/encrypt", json={"message": "Hello", "transitions": bad}
                )
                self.assertEqual(response.status_code, 400)

    def test_empty_and_non_string_messages_are_rejected(self):
        for bad in ("", "   \n", None, 123, ["a"]):
            with self.subTest(message=bad):
                response = self.client.post("/api/encrypt", json={"message": bad, "transitions": 2})
                self.assertEqual(response.status_code, 400)

    def test_oversized_message_is_rejected(self):
        response = self.encrypt("a" * (MAX_MESSAGE_LENGTH + 1))
        self.assertEqual(response.status_code, 400)
        self.assertIn("limited", response.get_json()["error"])

    def test_oversized_request_body_returns_json_413(self):
        response = self.client.post("/api/encrypt", json={"message": "a" * 1_100_000})
        self.assertEqual(response.status_code, 413)
        self.assertFalse(response.get_json()["ok"])

    def test_non_object_json_bodies_are_rejected(self):
        for path in ("/api/encrypt", "/api/decrypt"):
            for raw in ("[1, 2]", '"text"', "5", "null", "{not json"):
                with self.subTest(path=path, body=raw):
                    response = self.client.post(path, data=raw, content_type="application/json")
                    self.assertEqual(response.status_code, 400)

    def test_decrypt_requires_envelope_object_and_key(self):
        encrypted = self.encrypt().get_json()
        cases = [
            {"envelope": "nope", "key": encrypted["key"]},
            {"envelope": encrypted["envelope"]},
            {"envelope": encrypted["envelope"], "key": "   "},
            {"envelope": encrypted["envelope"], "key": 5},
            {"envelope": encrypted["envelope"], "key": "not-base64!!"},
            {"envelope": {}, "key": encrypted["key"]},
        ]
        for body in cases:
            with self.subTest(body=body):
                self.assertEqual(self.client.post("/api/decrypt", json=body).status_code, 400)

    # --- local-only protections --------------------------------------------

    def test_non_json_api_posts_are_rejected(self):
        for path in ("/api/encrypt", "/api/decrypt"):
            with self.subTest(path=path):
                response = self.client.post(path, data="message=hello")
                self.assertEqual(response.status_code, 415)

    def test_non_local_host_is_rejected(self):
        for host in ("example.com", "127.0.0.1.evil.test", "localhost.evil.test", "[::1]x", ""):
            with self.subTest(host=host):
                response = self.client.get("/", headers={"Host": host})
                self.assertEqual(response.status_code, 403)

    def test_local_hosts_with_ports_are_accepted(self):
        for host in ("127.0.0.1:8765", "localhost:8765", "LOCALHOST:8765"):
            with self.subTest(host=host):
                self.assertEqual(self.client.get("/api/health", headers={"Host": host}).status_code, 200)

    def test_foreign_origin_is_rejected(self):
        for origin in (
            "http://evil.example",
            "http://localhost:9999",
            "https://localhost",
            "null",
            "http://[::1",
            "http://localhost:8765/path",
            "http://user@localhost:8765",
        ):
            with self.subTest(origin=origin):
                response = self.client.post(
                    "/api/encrypt",
                    json={"message": "Hello", "transitions": 2},
                    headers={"Origin": origin},
                )
                self.assertEqual(response.status_code, 403)

    def test_same_origin_is_accepted(self):
        response = self.client.post(
            "/api/encrypt",
            json={"message": "Hello", "transitions": 2},
            headers={"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765"},
        )
        self.assertEqual(response.status_code, 200)

    def test_security_headers_are_present(self):
        response = self.client.get("/")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        csp = response.headers["Content-Security-Policy"]
        self.assertIn("script-src 'self'", csp)
        self.assertNotIn("unsafe-inline", csp)
        self.assertNotIn("unsafe-eval", csp)
        self.assertIn("frame-ancestors 'none'", csp)

    def test_api_responses_are_not_cached_and_have_no_cors(self):
        response = self.encrypt()
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_rejections_still_carry_security_headers(self):
        response = self.client.get("/", headers={"Host": "example.com"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_secret_key_is_never_in_the_envelope(self):
        payload = self.encrypt().get_json()
        self.assertNotIn(payload["key"], str(payload["envelope"]))


if __name__ == "__main__":
    unittest.main()
