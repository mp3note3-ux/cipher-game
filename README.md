# CipherKeys

CipherKeys is an educational, reversible cryptographic puzzle. It automatically chooses a text preparation route, then applies authenticated encryption and reversible keyboard-layout puzzle transformations.

> **Security note:** AES-256-GCM provides the cryptographic protection. Keyboard layouts and Base32 are representation/puzzle layers only; they do not add cryptographic strength. This project is for learning and experimentation, not a reviewed production protocol.

Current release: **1.1.0** (see [CHANGELOG.md](CHANGELOG.md)). Requires **Python 3.10+**.

## Features

- Automatic text routing: Hangul-only text uses Korean 2-beolsik; English, mixed-language, symbols, numbers, emoji and other scripts use UTF-8 directly.
- AES-256-GCM authenticated encryption with a fresh random 96-bit nonce.
- Base32 representation and reversible QWERTY, Dvorak and AZERTY key-position transformations.
- Separate puzzle JSON and 256-bit secret-key files.
- Local browser interface with Dashboard, Create Puzzle, Solve Puzzle, Encryption Explorer and Settings.
- Command-line interface that will not overwrite your key files by accident.

## Setup

Clone the repository, then create a virtual environment and install the dependencies.

**Windows (PowerShell)**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run the browser UI

```bash
python run_web.py
```

(Use `py run_web.py` on Windows if `python` is not on your PATH.) Then open **http://127.0.0.1:8765** in your browser.

Keep the terminal open while using CipherKeys. Press `Ctrl+C` in that terminal to stop the local server.

The browser UI is served by Flask on the loopback interface only (`127.0.0.1`). It does not expose a public network service and does not call a cloud API. The browser sends requests to the local Python process, which calls the `cipher_game` encryption engine.

### Browser UI sections

- **Dashboard:** shortcuts and a summary of the cryptography engine.
- **Create puzzle:** enter a message, see its automatically detected route, choose 2–4 keyboard transitions, and download the puzzle and key separately.
- **Solve puzzle:** load a puzzle JSON file and its matching key file to recover the message.
- **Encryption explorer:** educational explanations of all six pipeline stages.
- **Settings:** theme (follows your system setting until you choose one) and default keyboard transition preferences.

Messages and keys are not saved to browser storage or activity history. Only the theme and default-transition preferences are stored, in `localStorage`. The key is held in the active page's memory temporarily so it can be downloaded separately, and is cleared when the page is closed. Do not share screenshots or browser sessions that reveal a key.

## Command-line interface

Create a Korean puzzle:

```bash
python main.py encrypt --message "안녕"
```

Create an English puzzle:

```bash
python main.py encrypt --message "Hello, World!"
```

Decrypt:

```bash
python main.py decrypt --input puzzle.json --key-file shared.key
```

Both modes create a puzzle JSON file and a separate secret-key file.

### File safety

- `encrypt` **refuses to overwrite** an existing puzzle or key file and exits with an error. A key is the only way to open its puzzle, so replacing one makes every older puzzle made with it permanently undecryptable. Pass `--force` only when you really mean it, or choose other names with `--output` and `--key-file`.
- Both files are checked before either is written, so a refusal never leaves a half-written pair.
- On macOS and Linux the key file is created readable by you only (`0600`). Windows does not honour these permission bits; keep the key somewhere only you can access.
- Empty messages are rejected, and `--output` and `--key-file` must be different files.

### Exit codes

| Code | Meaning |
| ---- | ------- |
| `0`  | Success |
| `1`  | Error: bad input, unreadable or malformed file, refused overwrite, etc. |
| `2`  | `decrypt` only: authentication failed (wrong key, or the puzzle was modified) |

## How the encryption pipeline works

1. Detect the input route.
2. For Hangul-only input, convert Hangul to 2-beolsik keystrokes; otherwise keep the original text.
3. Encrypt the UTF-8 bytes with AES-256-GCM.
4. Base32-encode the ciphertext and authentication tag.
5. Apply a random sequence of reversible keyboard-layout transformations.
6. Store the puzzle metadata, nonce, and transformed text in JSON.

The public manifest (version, algorithm, encoding, input route, and layout sequence) is authenticated as AES-GCM associated data. Changing authenticated metadata causes verification to fail. The nonce is public and stored in the puzzle JSON.

The layout sequence is currently visible in the public manifest. Hiding it behind puzzle clues is a possible future mode and would require a versioned puzzle-format change.

### Limits

- Messages are limited to 20,000 characters (web and CLI).
- A puzzle may contain at most 8 keyboard transitions (9 layouts). The web UI offers 2–4. Files that exceed the limit are rejected when read.

## Versioning

Two numbers are deliberately separate:

| What | Where | Current value | Changes when |
| ---- | ----- | ------------- | ------------ |
| Application version | `cipher_game.__version__` | `1.1.0` | Any release. Shown in the UI and `/api/health`. |
| Puzzle format version | `cipher_game.puzzle.VERSION` | `2` | The puzzle JSON envelope changes. Stored in every puzzle file. |

Version 1 Korean-only puzzle files remain decryptable for backward compatibility.

## Security and privacy notes

- AES-GCM provides the cryptographic protection; keyboard transformations and Base32 do not add security.
- Keep `shared.key` private. Anyone with the key and puzzle can decrypt the message.
- Share the puzzle and key through separate channels.
- Never commit real key material to Git. The repository's `.gitignore` excludes `*.key`.
- The local browser server binds to `127.0.0.1`, rejects requests whose `Host` is not `localhost`/`127.0.0.1` (a DNS-rebinding defence), accepts only `application/json` for API writes, rejects foreign `Origin` headers, enables no CORS, sends a strict Content-Security-Policy with no inline scripts, sets no-store response headers, and does not enable Flask debug mode.
- This project has not undergone an independent security audit. Do not use it as a production secrets-management or secure-messaging system.

## Known limitations

These are design decisions, not bugs, and are left unchanged so the project has a stable base to build on.

- **The puzzle layers are not a challenge.** Keyboard layouts are applied to already-encrypted data, and the layout sequence is stored in the puzzle file. Someone who has the key can read the message directly; someone without it cannot make progress however well they understand the layouts.
- **The Korean route is narrow.** It only applies to messages made entirely of Hangul syllables and spaces. A single digit, punctuation mark or line break sends the message down the UTF-8 route (which loses nothing, but skips the Korean step).
- **Decomposed Hangul** (separate jamo, as some systems produce) is treated as ordinary UTF-8 text.
- **No license has been selected.** Until one is added, normal copyright restrictions apply.

## Tests

Install dependencies, then run:

```bash
python -m unittest discover -s tests -v
```

The suite (69 tests) covers:

- **Korean conversion:** every one of the 11,172 Hangul syllables, adjacent-syllable boundaries, and spaces.
- **Routing:** Korean vs UTF-8 selection, English and mixed-language recovery.
- **Layouts:** reversibility, generator bounds and invariants.
- **Integrity:** wrong key; tampered manifest, text mode, puzzle text and nonce; over-long layout sequences; invalid versions; backward compatibility with a hand-built version 1 puzzle.
- **CLI:** round trips, refusal to overwrite, `--force`, key-file permissions, exit codes, malformed input.
- **Web API:** local-only protections (Host, Origin, content type, security headers, no CORS), input validation, size limits, and round trips.

GitHub Actions runs the suite plus a JavaScript syntax check on Ubuntu, Windows and macOS with Python 3.10, 3.11, 3.12 and 3.13.

## Project layout

```text
cipher-game/
├── cipher_game/             # Cryptography engine
│   ├── crypto.py
│   ├── korean.py
│   ├── layouts.py
│   └── puzzle.py
├── webapp/
│   ├── app.py               # Local Flask API
│   ├── templates/index.html # Browser UI
│   └── static/
│       ├── app.css
│       └── app.js
├── tests/
│   ├── test_cipher_game.py  # Engine
│   ├── test_cli.py          # Command line
│   └── test_webapp.py       # Local web API
├── .github/workflows/tests.yml
├── CHANGELOG.md
├── main.py                  # CLI
├── run_web.py               # Browser UI launcher
└── requirements.txt
```

## License

No license has been selected yet. Until a license is added, normal copyright restrictions apply.
