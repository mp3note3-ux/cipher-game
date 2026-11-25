import unittest

from webapp.app import create_app


class CipherKeysWebAppTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()

    def test_home_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"CipherKeys", response.data)
        self.assertIn(b"Encryption explorer", response.data)

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["mode"], "local-only")

    def test_korean_round_trip(self):
        encrypted = self.client.post(
            "/api/encrypt",
            json={"message": "안녕", "transitions": 2},
        )
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
                encrypted = self.client.post(
                    "/api/encrypt",
                    json={"message": message, "transitions": 3},
                )
                self.assertEqual(encrypted.status_code, 200)
                payload = encrypted.get_json()
                self.assertEqual(payload["route"], "utf-8")
                decrypted = self.client.post(
                    "/api/decrypt",
                    json={"envelope": payload["envelope"], "key": payload["key"]},
                )
                self.assertEqual(decrypted.status_code, 200)
                self.assertEqual(decrypted.get_json()["message"], message)

    def test_wrong_key_fails_authentication(self):
        encrypted = self.client.post(
            "/api/encrypt",
            json={"message": "CipherKeys", "transitions": 2},
        ).get_json()
        wrong_key = "A" * 43 + "="
        response = self.client.post(
            "/api/decrypt",
            json={"envelope": encrypted["envelope"], "key": wrong_key},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Authentication failed", response.get_json()["error"])

    def test_invalid_transition_count_is_rejected(self):
        response = self.client.post(
            "/api/encrypt",
            json={"message": "Hello", "transitions": 9},
        )
        self.assertEqual(response.status_code, 400)

    def test_non_json_api_posts_are_rejected(self):
        response = self.client.post("/api/encrypt", data="message=hello")
        self.assertEqual(response.status_code, 415)

    def test_non_local_host_is_rejected(self):
        response = self.client.get("/", headers={"Host": "example.com"})
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
