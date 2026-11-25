"""Command-line interface for CipherKeys."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from cryptography.exceptions import InvalidTag

from cipher_game import create_puzzle, generate_key, key_from_text, key_to_text, solve_puzzle
from cipher_game.puzzle import KOREAN_MODE

PUZZLE_FILE_MODE = 0o644
KEY_FILE_MODE = 0o600  # owner-only on POSIX; Windows ignores most mode bits


def _check_can_write(path: Path, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(
            f"{path} already exists. Use --force to overwrite it "
            "(overwriting a key file makes older puzzles undecryptable)."
        )


def _write_text(path: Path, text: str, *, encoding: str, mode: int, force: bool) -> None:
    """Write a file without silently clobbering an existing one.

    Without ``force`` the file is created exclusively (O_EXCL), so a file that
    appears between the pre-check and the write is still never overwritten.
    The mode is applied at creation so a secret key is never briefly readable
    by other users.
    """
    flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if force else os.O_EXCL)
    fd = os.open(path, flags, mode)
    with os.fdopen(fd, "w", encoding=encoding, newline="\n") as handle:
        handle.write(text)
    try:
        os.chmod(path, mode)  # also tightens a pre-existing file when --force is used
    except OSError:
        pass


def _encrypt(args: argparse.Namespace) -> int:
    message = args.message if args.message is not None else input("Message: ")
    if not message.strip():
        raise ValueError("Message must not be empty.")

    puzzle_path = Path(args.output)
    key_path = Path(args.key_file)
    if puzzle_path.resolve() == key_path.resolve():
        raise ValueError("--output and --key-file must be different files.")
    # Check both paths before writing either, so we never leave a half-written pair.
    _check_can_write(puzzle_path, args.force)
    _check_can_write(key_path, args.force)

    key = generate_key()
    envelope = create_puzzle(message, key)

    _write_text(
        puzzle_path,
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        mode=PUZZLE_FILE_MODE,
        force=args.force,
    )
    _write_text(
        key_path,
        key_to_text(key) + "\n",
        encoding="ascii",
        mode=KEY_FILE_MODE,
        force=args.force,
    )

    route = (
        "Korean 2-beolsik"
        if envelope["text_mode"] == KOREAN_MODE
        else "UTF-8 (English, mixed, or other text)"
    )
    print(f"Detected input route: {route}")
    print(f"Puzzle saved to: {puzzle_path}")
    print(f"Secret key saved to: {key_path}")
    print("Share the puzzle file and key through separate channels.")
    print("Do not commit the key file to Git.")
    return 0


def _decrypt(args: argparse.Namespace) -> int:
    envelope = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(envelope, dict):
        raise ValueError("The puzzle file must contain a JSON object.")
    # utf-8-sig tolerates a BOM added by some Windows editors.
    key = key_from_text(Path(args.key_file).read_text(encoding="utf-8-sig"))
    try:
        message = solve_puzzle(envelope, key)
    except InvalidTag:
        print("Decryption failed: wrong key or modified puzzle data.", file=sys.stderr)
        return 2
    print(f"Recovered message: {message}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create and solve layered multilingual keyboard cryptography puzzles."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    encrypt_parser = subparsers.add_parser("encrypt", help="Create a new puzzle")
    encrypt_parser.add_argument("--message", help="Message to encrypt (or omit to be prompted)")
    encrypt_parser.add_argument("--output", default="puzzle.json", help="Puzzle output file")
    encrypt_parser.add_argument("--key-file", default="shared.key", help="Separate secret-key file")
    encrypt_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing puzzle/key files (older puzzles using an overwritten key become undecryptable)",
    )
    encrypt_parser.set_defaults(func=_encrypt)

    decrypt_parser = subparsers.add_parser("decrypt", help="Solve an existing puzzle")
    decrypt_parser.add_argument("--input", default="puzzle.json", help="Puzzle JSON file")
    decrypt_parser.add_argument("--key-file", default="shared.key", help="Secret-key file")
    decrypt_parser.set_defaults(func=_decrypt)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
