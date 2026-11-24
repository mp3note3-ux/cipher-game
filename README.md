# CipherKeys

CipherKeys is an educational, reversible cryptographic puzzle. It automatically chooses a text preparation route, then applies authenticated encryption and reversible keyboard-layout puzzle transformations.

> **Security note:** AES-256-GCM provides the cryptographic protection. Keyboard layouts and Base32 are representation/puzzle layers only; they do not add cryptographic strength. This project is for learning and experimentation, not a reviewed production protocol.

## Automatic input detection

No language flag is required:

- **Hangul route:** text consisting only of precomposed Hangul syllables and ordinary spaces is converted to standard Korean 2-beolsik keystrokes before encryption. For example, `안녕` becomes `dkssud`.
- **UTF-8 route:** English, punctuation, numbers, emoji, other scripts, and mixed-language text are encrypted as their original UTF-8 bytes. This preserves the input exactly, including mixed Korean/English messages.

Both routes use AES-256-GCM, Base32, and a randomly selected sequence of reversible QWERTY, Dvorak, and AZERTY key-position transformations. The selected route is recorded in the puzzle manifest, so decryption selects the matching reverse process automatically.

## How it works

1. Detect the input route.
2. For Hangul-only input, convert Hangul to 2-beolsik keystrokes; otherwise, keep the original text.
3. Encrypt the UTF-8 bytes with AES-256-GCM.
4. Base32-encode the ciphertext and authentication tag.
5. Apply a random sequence of reversible keyboard-layout transformations.
6. Store the puzzle metadata, nonce, and transformed text in JSON.

The public manifest (version, algorithm, encoding, input route, and layout sequence) is authenticated as AES-GCM associated data. Modifying that metadata causes authentication to fail. The nonce is public and is stored in the puzzle JSON. A fresh 96-bit nonce is generated for each encryption.

Version 1 Korean-only puzzle files remain decryptable for backward compatibility.

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

## Create puzzles

Korean:

```powershell
python main.py encrypt --message "안녕"
```

English:

```powershell
python main.py encrypt --message "Hello, World!"
```

Mixed-language:

```powershell
python main.py encrypt --message "안녕, hello!"
```

CipherKeys automatically chooses the route and reports it. Each command creates:

- `puzzle.json` — the puzzle, nonce, and public transformation manifest.
- `shared.key` — the secret AES-256 key in Base64 text form.

Send the puzzle and key through **separate channels**. Anyone who obtains the key can decrypt the puzzle. Never commit `shared.key` or other real key material to Git.

## Solve a puzzle

```powershell
python main.py decrypt --input puzzle.json --key-file shared.key
```

The recipient does not need to specify the language. The authenticated manifest tells CipherKeys which reverse text path to use.

## Run tests

```powershell
python -m unittest discover -s tests -v
```

Tests cover automatic route selection, Korean/English/mixed-language round-trips, reversible keyboard transformations, wrong-key rejection, and metadata tampering.

## Current scope and limitations

- Korean keyboard conversion currently supports precomposed Hangul syllables and ordinary spaces. Korean input containing punctuation or Latin characters uses the UTF-8 route to preserve it exactly.
- The layout sequence is included in the public manifest in this version, so the recipient does not yet have to infer it from clues. A future puzzle mode can hide the sequence behind clues.
- Keyboard layouts operate on the 26 QWERTY letter-key positions. Some target positions become punctuation (for example, Dvorak and AZERTY); this is expected and reversible.
- AES-GCM keys must be kept secret. Never reuse a nonce with the same key. CipherKeys generates a fresh random nonce for each encryption.
- The key file is deliberately separate from the puzzle file and is excluded by `.gitignore`.

## Project layout

```text
cipher-game/
├── cipher_game/
│   ├── __init__.py
│   ├── crypto.py
│   ├── korean.py
│   ├── layouts.py
│   └── puzzle.py
├── tests/
│   └── test_cipher_game.py
├── main.py
├── requirements.txt
└── README.md
```

## License

No license has been selected yet. Until a license is added, normal copyright restrictions apply.
