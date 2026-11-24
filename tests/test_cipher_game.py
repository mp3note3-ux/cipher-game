import unittest

from cryptography.exceptions import InvalidTag

from cipher_game import create_puzzle, generate_key, solve_puzzle
from cipher_game.korean import hangul_to_2beolsik, keys_to_hangul
from cipher_game.layouts import apply_layout_sequence, reverse_layout_sequence, transform_layout


class KoreanKeyboardTests(unittest.TestCase):
    def test_example_maps_to_expected_keystrokes(self):
        self.assertEqual(hangul_to_2beolsik("안녕"), "dkssud")

    def test_common_hangul_round_trips(self):
        examples = ["안녕", "한글", "사랑", "가나다", "학교", "먹고", "값이", "읽어", "안녕 세상"]
        for original in examples:
            with self.subTest(original=original):
                self.assertEqual(keys_to_hangul(hangul_to_2beolsik(original)), original)


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


class PuzzleTests(unittest.TestCase):
    def test_puzzle_round_trip(self):
        key = generate_key()
        envelope = create_puzzle("안녕", key, ["qwerty", "dvorak", "azerty"])
        self.assertEqual(solve_puzzle(envelope, key), "안녕")

    def test_wrong_key_is_rejected(self):
        envelope = create_puzzle("안녕", generate_key(), ["qwerty", "azerty"])
        with self.assertRaises(InvalidTag):
            solve_puzzle(envelope, generate_key())

    def test_modified_metadata_is_rejected(self):
        key = generate_key()
        envelope = create_puzzle("안녕", key, ["qwerty", "dvorak"])
        envelope["layout_sequence"] = ["qwerty", "azerty"]
        with self.assertRaises((InvalidTag, ValueError)):
            solve_puzzle(envelope, key)


if __name__ == "__main__":
    unittest.main()
