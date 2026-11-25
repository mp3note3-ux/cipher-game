import contextlib
import io
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

import main as cli


def run_cli(*argv):
    """Run the CLI, returning (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.puzzle = self.dir / "puzzle.json"
        self.key = self.dir / "shared.key"

    def encrypt(self, message="Hello, World!", *extra):
        return run_cli(
            "encrypt", "--message", message,
            "--output", str(self.puzzle), "--key-file", str(self.key), *extra,
        )

    def decrypt(self):
        return run_cli("decrypt", "--input", str(self.puzzle), "--key-file", str(self.key))

    def test_round_trip(self):
        for message in ("Hello, World!", "안녕", "안녕 Hello 🔐"):
            with self.subTest(message=message):
                code, _, _ = self.encrypt(message, "--force")
                self.assertEqual(code, 0)
                code, out, _ = self.decrypt()
                self.assertEqual(code, 0)
                self.assertIn(message, out)

    def test_refuses_to_overwrite_existing_key_and_puzzle(self):
        self.assertEqual(self.encrypt("first")[0], 0)
        original_key = self.key.read_text()
        original_puzzle = self.puzzle.read_text(encoding="utf-8")

        code, _, err = self.encrypt("second")
        self.assertEqual(code, 1)
        self.assertIn("--force", err)
        self.assertEqual(self.key.read_text(), original_key)
        self.assertEqual(self.puzzle.read_text(encoding="utf-8"), original_puzzle)

    def test_refuses_when_only_key_exists_and_leaves_no_partial_output(self):
        self.key.write_text("existing-key\n")
        code, _, err = self.encrypt("hello")
        self.assertEqual(code, 1)
        self.assertIn("already exists", err)
        self.assertFalse(self.puzzle.exists())
        self.assertEqual(self.key.read_text(), "existing-key\n")

    def test_force_overwrites(self):
        self.assertEqual(self.encrypt("first")[0], 0)
        old_key = self.key.read_text()
        self.assertEqual(self.encrypt("second", "--force")[0], 0)
        self.assertNotEqual(self.key.read_text(), old_key)
        self.assertIn("second", self.decrypt()[1])

    @unittest.skipIf(os.name == "nt", "POSIX permission bits are not meaningful on Windows")
    def test_key_file_is_owner_only(self):
        self.assertEqual(self.encrypt()[0], 0)
        mode = stat.S_IMODE(self.key.stat().st_mode)
        self.assertEqual(mode & 0o077, 0, msg=f"key file mode was {oct(mode)}")

    @unittest.skipIf(os.name == "nt", "POSIX permission bits are not meaningful on Windows")
    def test_force_tightens_permissions_of_existing_key(self):
        self.key.write_text("old\n")
        os.chmod(self.key, 0o644)
        self.assertEqual(self.encrypt("x", "--force")[0], 0)
        self.assertEqual(stat.S_IMODE(self.key.stat().st_mode) & 0o077, 0)

    def test_output_and_key_file_must_differ(self):
        code, _, err = run_cli(
            "encrypt", "--message", "x",
            "--output", str(self.puzzle), "--key-file", str(self.puzzle),
        )
        self.assertEqual(code, 1)
        self.assertIn("different", err)

    def test_empty_message_is_rejected(self):
        code, _, err = self.encrypt("   ")
        self.assertEqual(code, 1)
        self.assertIn("empty", err)
        self.assertFalse(self.puzzle.exists())
        self.assertFalse(self.key.exists())

    def test_wrong_key_returns_exit_code_2(self):
        self.assertEqual(self.encrypt()[0], 0)
        other_key = self.dir / "other.key"
        other_dir_puzzle = self.dir / "other.json"
        run_cli("encrypt", "--message", "x", "--output", str(other_dir_puzzle), "--key-file", str(other_key))
        code, _, err = run_cli("decrypt", "--input", str(self.puzzle), "--key-file", str(other_key))
        self.assertEqual(code, 2)
        self.assertIn("Decryption failed", err)

    def test_tampered_puzzle_returns_exit_code_2(self):
        self.assertEqual(self.encrypt("Hello")[0], 0)
        data = json.loads(self.puzzle.read_text(encoding="utf-8"))
        data["text_mode"] = "korean-2beolsik" if data["text_mode"] == "utf-8" else "utf-8"
        self.puzzle.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(self.decrypt()[0], 2)

    def test_non_object_puzzle_json_is_a_clean_error(self):
        self.puzzle.write_text("[1, 2, 3]", encoding="utf-8")
        self.key.write_text("A" * 43 + "=\n")
        code, _, err = self.decrypt()
        self.assertEqual(code, 1)
        self.assertIn("JSON object", err)

    def test_invalid_json_and_missing_files_are_clean_errors(self):
        self.puzzle.write_text("{not json", encoding="utf-8")
        self.key.write_text("A" * 43 + "=\n")
        self.assertEqual(self.decrypt()[0], 1)
        self.puzzle.unlink()
        self.assertEqual(self.decrypt()[0], 1)

    def test_key_file_with_bom_is_accepted(self):
        self.assertEqual(self.encrypt("bom test")[0], 0)
        self.key.write_bytes(b"\xef\xbb\xbf" + self.key.read_bytes())
        code, out, _ = self.decrypt()
        self.assertEqual(code, 0)
        self.assertIn("bom test", out)


if __name__ == "__main__":
    unittest.main()
