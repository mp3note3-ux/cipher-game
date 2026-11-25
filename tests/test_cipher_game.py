import base64
import unittest

from cryptography.exceptions import InvalidTag

from cipher_game import create_puzzle, generate_key, solve_puzzle
from cipher_game.korean import S_BASE, S_COUNT, hangul_to_2beolsik, keys_to_hangul
from cipher_game.layouts import (
    LAYOUTS,
    MAX_SEQUENCE_LENGTH,
    MAX_TRANSITIONS,
    apply_layout_sequence,
    generate_layout_sequence,
    reverse_layout_sequence,
    transform_layout,
)
from cipher_game.puzzle import (
    KOREAN_MODE,
    MAX_MESSAGE_LENGTH,
    UTF8_MODE,
    detect_text_mode,
)


class KoreanKeyboardTests(unittest.TestCase):
    def test_example_maps_to_expected_keystrokes(self):
        self.assertEqual(hangul_to_2beolsik("안녕"), "dkssud")

    def test_common_hangul_round_trips(self):
        examples = ["안녕", "한글", "사랑", "가나다", "학교", "먹고", "값이", "읽어", "안녕 세상"]
        for original in examples:
            with self.subTest(original=original):
                self.assertEqual(keys_to_hangul(hangul_to_2beolsik(original)), original)

    def test_every_precomposed_syllable_round_trips(self):
        """All 11,172 syllables, each on its own."""
        for offset in range(S_COUNT):
            syllable = chr(S_BASE + offset)
            self.assertEqual(
                keys_to_hangul(hangul_to_2beolsik(syllable)),
                syllable,
                msg=f"U+{ord(syllable):04X} failed to round-trip",
            )

    def test_syllable_pairs_round_trip_across_boundaries(self):
        """Adjacent syllables are where keystroke ambiguity would show up.

        Every syllable is paired with a deterministic, well-spread partner,
        plus a full sweep of (final consonant x next initial x next vowel).
        """
        for offset in range(S_COUNT):
            first = chr(S_BASE + offset)
            second = chr(S_BASE + (offset * 7919 + 13) % S_COUNT)
            text = first + second
            self.assertEqual(keys_to_hangul(hangul_to_2beolsik(text)), text, msg=text)

        # 28 finals x 19 initials x 21 vowels boundary sweep.
        for final in range(28):
            for initial in range(19):
                for vowel in range(21):
                    first = chr(S_BASE + (0 * 21 + 0) * 28 + final)           # 가 + final
                    second = chr(S_BASE + (initial * 21 + vowel) * 28)         # initial + vowel
                    text = first + second
                    self.assertEqual(keys_to_hangul(hangul_to_2beolsik(text)), text, msg=text)

    def test_spaces_between_syllables_round_trip(self):
        for text in ("가 나", "값 읽", " 가", "가 ", "닭  닭"):
            with self.subTest(text=text):
                self.assertEqual(keys_to_hangul(hangul_to_2beolsik(text)), text)

    def test_non_hangul_is_rejected_by_converter(self):
        with self.assertRaises(ValueError):
            hangul_to_2beolsik("a")


class AutomaticRouteTests(unittest.TestCase):
    def test_hangul_only_text_uses_korean_route(self):
        self.assertEqual(detect_text_mode("안녕"), KOREAN_MODE)
        self.assertEqual(detect_text_mode("안녕 세상"), KOREAN_MODE)

    def test_english_and_mixed_text_use_utf8_route(self):
        examples = [
            "Hello World!",
            "Hello, 안녕!",
            "안녕!",
            "こんにちは",
            "Hello 🔐",
            "12345",
        ]
        for message in examples:
            with self.subTest(message=message):
                self.assertEqual(detect_text_mode(message), UTF8_MODE)

    def test_non_string_is_rejected(self):
        with self.assertRaises(TypeError):
            detect_text_mode(123)  # type: ignore[arg-type]

    def test_english_round_trip(self):
        key = generate_key()
        envelope = create_puzzle("Hello, World! 123", key, ["qwerty", "dvorak", "azerty"])
        self.assertEqual(envelope["text_mode"], UTF8_MODE)
        self.assertEqual(solve_puzzle(envelope, key), "Hello, World! 123")

    def test_mixed_language_round_trip_preserves_original_text(self):
        message = "안녕, hello! こんにちは 🔐"
        key = generate_key()
        envelope = create_puzzle(message, key, ["qwerty", "azerty", "dvorak"])
        self.assertEqual(envelope["text_mode"], UTF8_MODE)
        self.assertEqual(solve_puzzle(envelope, key), message)

    def test_korean_round_trip_selects_keyboard_route(self):
        key = generate_key()
        envelope = create_puzzle("안녕", key, ["qwerty", "dvorak"])
        self.assertEqual(envelope["text_mode"], KOREAN_MODE)
        self.assertEqual(solve_puzzle(envelope, key), "안녕")

    def test_text_mode_metadata_is_authenticated(self):
        key = generate_key()
        envelope = create_puzzle("안녕", key, ["qwerty", "dvorak"])
        envelope["text_mode"] = UTF8_MODE
        with self.assertRaises(InvalidTag):
            solve_puzzle(envelope, key)

    def test_maximum_length_message_round_trips(self):
        message = "가" * MAX_MESSAGE_LENGTH
        key = generate_key()
        self.assertEqual(solve_puzzle(create_puzzle(message, key), key), message)

    def test_over_length_message_is_rejected(self):
        with self.assertRaises(ValueError):
            create_puzzle("a" * (MAX_MESSAGE_LENGTH + 1), generate_key())


class LayoutTests(unittest.TestCase):
    def test_every_layout_pair_is_reversible(self):
        layouts = {
            "qwerty": "qwertyuiopasdfghjklzxcvbnm",
            "dvorak": "',.pyfgcrlaoeuidhtn;qjkxbm",
            "azerty": "azertyuiopqsdfghjklwxcvbn,",
        }
        for source, sample in layouts.items():
            for target in layouts:
                sample_text = sample + "234567"
                transformed = transform_layout(sample_text, source, target)
                self.assertEqual(transform_layout(transformed, target, source), sample_text)

    def test_sequence_is_reversible(self):
        sample = "cipher puzzle 123"
        sequence = ["qwerty", "dvorak", "azerty", "qwerty"]
        transformed = apply_layout_sequence(sample, sequence)
        self.assertEqual(reverse_layout_sequence(transformed, sequence), sample)

    def test_generated_sequences_are_well_formed(self):
        for transitions in range(1, MAX_TRANSITIONS + 1):
            sequence = generate_layout_sequence(transitions)
            self.assertEqual(len(sequence), transitions + 1)
            self.assertEqual(sequence[0], "qwerty")
            self.assertTrue(all(item in LAYOUTS for item in sequence))
            self.assertTrue(all(a != b for a, b in zip(sequence, sequence[1:])))

    def test_generated_sequence_bounds(self):
        for bad in (0, -1, MAX_TRANSITIONS + 1, True, 2.5, "3"):
            with self.subTest(transitions=bad):
                with self.assertRaises(ValueError):
                    generate_layout_sequence(bad)  # type: ignore[arg-type]


class PuzzleIntegrityTests(unittest.TestCase):
    def test_wrong_key_is_rejected(self):
        envelope = create_puzzle("안녕", generate_key(), ["qwerty", "azerty"])
        with self.assertRaises(InvalidTag):
            solve_puzzle(envelope, generate_key())

    def test_modified_layout_metadata_is_rejected(self):
        key = generate_key()
        envelope = create_puzzle("안녕", key, ["qwerty", "dvorak"])
        envelope["layout_sequence"] = ["qwerty", "azerty"]
        with self.assertRaises((InvalidTag, ValueError)):
            solve_puzzle(envelope, key)

    def test_modified_puzzle_text_is_rejected(self):
        key = generate_key()
        envelope = create_puzzle("Hello, World!", key, ["qwerty", "dvorak"])
        envelope["puzzle_text"] = envelope["puzzle_text"][::-1]
        with self.assertRaises((InvalidTag, ValueError)):
            solve_puzzle(envelope, key)

    def test_modified_nonce_is_rejected(self):
        key = generate_key()
        envelope = create_puzzle("Hello", key, ["qwerty", "dvorak"])
        envelope["nonce"] = base64.b64encode(bytes(12)).decode("ascii")
        with self.assertRaises(InvalidTag):
            solve_puzzle(envelope, key)

    def test_wrong_length_nonce_is_rejected(self):
        key = generate_key()
        envelope = create_puzzle("Hello", key, ["qwerty", "dvorak"])
        envelope["nonce"] = base64.b64encode(bytes(8)).decode("ascii")
        with self.assertRaises(ValueError):
            solve_puzzle(envelope, key)

    def test_overlong_layout_sequence_is_rejected_on_read(self):
        key = generate_key()
        envelope = create_puzzle("Hello", key, ["qwerty", "dvorak"])
        envelope["layout_sequence"] = ["qwerty", "dvorak"] * (MAX_SEQUENCE_LENGTH + 5)
        with self.assertRaisesRegex(ValueError, "layout sequence"):
            solve_puzzle(envelope, key)

    def test_overlong_layout_sequence_is_rejected_on_create(self):
        sequence = ["qwerty", "dvorak"] * (MAX_SEQUENCE_LENGTH + 5)
        with self.assertRaises(ValueError):
            create_puzzle("Hello", generate_key(), sequence)

    def test_maximum_length_layout_sequence_is_accepted(self):
        key = generate_key()
        sequence = generate_layout_sequence(MAX_TRANSITIONS)
        envelope = create_puzzle("Hello", key, sequence)
        self.assertEqual(solve_puzzle(envelope, key), "Hello")

    def test_non_integer_versions_are_rejected(self):
        key = generate_key()
        for bad_version in (True, 2.0, "2", None, 3, 0):
            with self.subTest(version=bad_version):
                envelope = create_puzzle("Hello", key, ["qwerty", "dvorak"])
                envelope["version"] = bad_version
                with self.assertRaises(ValueError):
                    solve_puzzle(envelope, key)

    def test_non_dict_envelope_is_rejected(self):
        for bad in (None, [], "puzzle", 5):
            with self.subTest(envelope=bad):
                with self.assertRaises(ValueError):
                    solve_puzzle(bad, generate_key())  # type: ignore[arg-type]

    def test_missing_fields_are_rejected(self):
        key = generate_key()
        for field in ("puzzle_text", "nonce", "text_mode", "layout_sequence"):
            with self.subTest(field=field):
                envelope = create_puzzle("Hello", key, ["qwerty", "dvorak"])
                del envelope[field]
                with self.assertRaises(ValueError):
                    solve_puzzle(envelope, key)

    def test_legacy_v1_korean_puzzle_still_decrypts(self):
        """Version 1 puzzles have no text_mode and always use the Korean route."""
        from cipher_game.crypto import encrypt_bytes
        from cipher_game.puzzle import _canonical_manifest

        key = generate_key()
        sequence = ["qwerty", "dvorak"]
        manifest = {
            "version": 1,
            "algorithm": "AES-256-GCM",
            "encoding": "BASE32",
            "layout_sequence": sequence,
        }
        nonce, blob = encrypt_bytes(
            key, hangul_to_2beolsik("안녕").encode("utf-8"), _canonical_manifest(manifest)
        )
        encoded = base64.b32encode(blob).decode("ascii").rstrip("=").lower()
        envelope = {
            **manifest,
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "puzzle_text": apply_layout_sequence(encoded, sequence),
        }
        self.assertEqual(solve_puzzle(envelope, key), "안녕")


if __name__ == "__main__":
    unittest.main()
