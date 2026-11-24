# CipherKeys

CipherKeys is an educational, reversible cryptographic puzzle built around Korean 2-beolsik keyboard input. It combines a real authenticated-encryption primitive with reversible keyboard-layout transformations.

> **Security note:** AES-256-GCM provides the cryptographic protection. Keyboard layouts and Base32 are puzzle/representation layers only; they do not add cryptographic strength. This project is for learning and experimentation, not a reviewed production protocol.

## What it does

For the example message `안녕`, standard Korean 2-beolsik input produces `dkssud`. CipherKeys then:

1. Converts supported Hangul syllables into 2-beolsik keystrokes.
2. Encrypts those UTF-8 bytes with AES-256-GCM.
3. Base32-encodes the ciphertext and authentication tag.
4. Applies a randomly selected sequence of reversible QWERTY, Dvorak, and AZERTY key-position transformations.
5. Writes a JSON puzzle and a separate 256-bit secret-key file.

The recipient reverses the layout steps, Base32-decodes, authenticates/decrypts with AES-GCM, and converts the keystrokes back into Hangul.

The public puzzle manifest (algorithm, encoding, version, and layout sequence) is authenticated as AES-GCM associated data. Changing that metadata causes authentication to fail. The nonce is public and is stored in the puzzle JSON. A fresh 96-bit nonce is generated for every encryption under a key.

## Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux

## Setup (Windows PowerShell / VS Code)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use the virtual-environment interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Create a puzzle

```powershell
python main.py encrypt --message "안녕"
```

This creates:

- `puzzle.json` — the puzzle, nonce, and public transformation manifest.
- `shared.key` — the secret AES-256 key in Base64 text form.

Send the puzzle and key to the recipient through **separate channels**. Anyone who obtains the key can decrypt the puzzle. Never commit `shared.key` or other real key material to Git.

## Solve a puzzle

```powershell
python main.py decrypt --input puzzle.json --key-file shared.key
```

Expected output:

```text
Recovered message: 안녕
```

## Run tests

```powershell
python -m unittest discover -s tests -v
```

Tests cover Korean keyboard round-trips, reversible layout transformations, successful puzzle recovery, wrong-key rejection, and tampered metadata rejection.

## Current scope and limitations

- The initial Korean converter supports precomposed Hangul syllables and spaces. It deliberately rejects other characters rather than silently creating ambiguous output.
- Keyboard layouts operate on 26 letter-key positions. Some Dvorak/AZERTY positions become punctuation; this is expected and reversible.
- The layout sequence is included in the public manifest in this first version, so the recipient does not yet have to infer it from clues. Later puzzle versions can hide the sequence behind clues while retaining enough information to solve it.
- AES-GCM keys must be kept secret. Do not reuse a nonce with the same key. This application generates a fresh random nonce for each encryption.
- The key file is deliberately separate from the puzzle file and is excluded by `.gitignore`.

## Project layout

```text
cipher-game/
├── cipher_game/
│   ├── __init__.py
│   ├── crypto.py       # AES-256-GCM and key serialization
│   ├── korean.py       # Hangul / 2-beolsik conversion
│   ├── layouts.py      # Reversible keyboard-layout transformations
│   └── puzzle.py       # Puzzle envelope and reverse pipeline
├── tests/
│   └── test_cipher_game.py
├── main.py
├── requirements.txt
└── README.md
```

## License

No license has been selected yet. Until a license is added, normal copyright restrictions apply.
