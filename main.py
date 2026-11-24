"""Command-line interface for CipherKeys."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from cryptography.exceptions import InvalidTag

from cipher_game import create_puzzle, generate_key, key_from_text, key_to_text, solve_puzzle


def _encrypt(args: argparse.Namespace) -> int:
    message = args.message if args.message is not None else input("Korean message: ")
    key = generate_key()
    envelope = create_puzzle(message, key)

    puzzle_path = Path(args.output)
    key_path = Path(args.key_file)
    puzzle_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    key_path.write_text(key_to_text(key) + "\n", encoding="ascii")

    print(f"Puzzle saved to: {puzzle_path}")
    print(f"Secret key saved to: {key_path}")
    print("Share the puzzle file and key through separate channels.")
    print("Do not commit the key file to Git.")
    return 0


def _decrypt(args: argparse.Namespace) -> int:
    envelope = json.loads(Path(args.input).read_text(encoding="utf-8"))
    key = key_from_text(Path(args.key_file).read_text(encoding="ascii"))
    try:
        message = solve_puzzle(envelope, key)
    except InvalidTag:
        print("Decryption failed: wrong key or modified puzzle data.", file=sys.stderr)
        return 2
    print(f"Recovered message: {message}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create and solve layered Korean keyboard cryptography puzzles."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    encrypt_parser = subparsers.add_parser("encrypt", help="Create a new puzzle")
    encrypt_parser.add_argument("--message", help="Korean message (or omit to be prompted)")
    encrypt_parser.add_argument("--output", default="puzzle.json", help="Puzzle output file")
    encrypt_parser.add_argument("--key-file", default="shared.key", help="Separate secret-key file")
    encrypt_parser.set_defaults(func=_encrypt)

    decrypt_parser = subparsers.add_parser("decrypt", help="Solve an existing puzzle")
    decrypt_parser.add_argument("--input", default="puzzle.json", help="Puzzle JSON file")
    decrypt_parser.add_argument("--key-file", default="shared.key", help="Secret-key file")
    decrypt_parser.set_defaults(func=_decrypt)

    args = parser.parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
