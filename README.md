# CipherKeys

CipherKeys is an educational, reversible cryptographic puzzle. It automatically chooses a text preparation route, then applies authenticated encryption and reversible keyboard-layout puzzle transformations.

> **Security note:** AES-256-GCM provides the cryptographic protection. Keyboard layouts and Base32 are representation/puzzle layers only; they do not add cryptographic strength. This project is for learning and experimentation, not a reviewed production protocol.

## Features

- Automatic text routing: Hangul-only text uses Korean 2-beolsik; English, mixed-language, symbols, numbers, emoji and other scripts use UTF-8 directly.
- AES-256-GCM authenticated encryption with a fresh random 96-bit nonce.
- Base32 representation and reversible QWERTY, Dvorak and AZERTY key-position transformations.
- Separate puzzle JSON and 256-bit secret-key files.
- Local browser interface with Dashboard, Create Puzzle, Solve Puzzle, Encryption Explorer and Settings.
- Command-line interface remains available.

## Automatic input detection

No language flag is required:

- **Hangul route:** text consisting only of precomposed Hangul syllables and ordinary spaces is converted to standard Korean 2-beolsik keystrokes. For example, `안녕` becomes `dkssud`.
- **UTF-8 route:** English, punctuation, numbers, emoji, other scripts, and mixed-language text are encrypted as their original UTF-8 bytes.

The selected route is recorded in the puzzle manifest. Both routes use the same AES-256-GCM, Base32 and keyboard-layout puzzle layers.

## Run the browser UI (Windows / VS Code)

Open PowerShell in the repository folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run_web.py
```

Then open **http://127.0.0.1:8765** in your browser.

Keep the terminal open while using CipherKeys. Press `Ctrl+C` in that terminal to stop the local server.

The browser UI is served by Flask on the loopback interface only (`127.0.0.1`). It does not expose a public network service and does not call a cloud API. The browser sends requests to the local Python process, which calls the existing `cipher_game` encryption engine.

### Browser UI sections

- **Dashboard:** shortcuts and a summary of the cryptography engine.
- **Create puzzle:** enter a message, see its automatically detected route, choose 2–4 keyboard transitions, and download the puzzle and key separately.
- **Solve puzzle:** load a puzzle JSON file and its matching key file to recover the message.
- **Encryption explorer:** educational explanations of all six pipeline stages.
- **Settings:** theme and default keyboard transition preferences.

Messages and keys are not saved to browser storage or activity history. The key is held in the active page's memory temporarily so it can be downloaded separately. Do not share screenshots or browser sessions that reveal a key.

## Command-line interface

The original CLI is still available.

Create a Korean puzzle:

```powershell
python main.py encrypt --message "안녕"
```

Create an English puzzle:

```powershell
python main.py encrypt --message "Hello, World!"
```

Decrypt:

```powershell
python main.py decrypt --input puzzle.json --key-file shared.key
```

Both modes create a puzzle JSON file and a separate secret-key file.

## How the encryption pipeline works

1. Detect the input route.
2. For Hangul-only input, convert Hangul to 2-beolsik keystrokes; otherwise keep the original text.
3. Encrypt the UTF-8 bytes with AES-256-GCM.
4. Base32-encode the ciphertext and authentication tag.
5. Apply a random sequence of reversible keyboard-layout transformations.
6. Store the puzzle metadata, nonce, and transformed text in JSON.

The public manifest (version, algorithm, encoding, input route, and layout sequence) is authenticated as AES-GCM associated data. Changing authenticated metadata causes verification to fail. The nonce is public and stored in the puzzle JSON.

The layout sequence is currently visible in the public manifest. Hiding it behind puzzle clues is a possible future mode and would require a versioned puzzle-format change.

## Security and privacy notes

- AES-GCM provides the cryptographic protection; keyboard transformations and Base32 do not add security.
- Keep `shared.key` private. Anyone with the key and puzzle can decrypt the message.
- Share the puzzle and key through separate channels.
- Never commit real key material to Git. The repository's `.gitignore` excludes `*.key`.
- The local browser server binds to `127.0.0.1`, disables cross-origin browser access, sets no-store response headers and does not enable Flask debug mode.
- This project has not undergone an independent security audit. Do not use it as a production secrets-management or secure-messaging system.
- Version 1 Korean-only puzzle files remain decryptable for backward compatibility.

## Tests

Install dependencies, then run:

```powershell
python -m unittest discover -s tests -v
```

The test suite covers Korean keyboard conversion, automatic Korean/UTF-8 selection, English and mixed-language recovery, keyboard mapping reversibility, wrong-key rejection, metadata tampering, and the local web API.

## Project layout

```text
cipher-game/
├── cipher_game/             # Existing cryptography engine
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
├── main.py                  # Original CLI
├── run_web.py               # Browser UI launcher
└── requirements.txt
```

## License

No license has been selected yet. Until a license is added, normal copyright restrictions apply.
