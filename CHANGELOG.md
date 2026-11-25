# Changelog

All notable changes to CipherKeys are documented here. The project follows
[Semantic Versioning](https://semver.org/) for the **application** version
(`cipher_game.__version__`). The **puzzle file format** has its own number
(`cipher_game.puzzle.VERSION`, currently `2`) that only changes when the JSON
envelope changes; version 1 and version 2 puzzles are both still readable.

## [1.1.0] — Hardening and cleanup release

No new features and no puzzle-format change: puzzles created by 1.0 still
decrypt in 1.1, and 1.1 puzzles decrypt in 1.0.

### Fixed — data safety
- **CLI no longer silently overwrites files.** `encrypt` previously replaced an
  existing `shared.key` and `puzzle.json`, making every older puzzle for that key
  permanently undecryptable. It now refuses and exits with code 1 unless
  `--force` is given. Both paths are checked before either file is written, so a
  failure cannot leave a half-written puzzle/key pair, and files are created
  exclusively (`O_EXCL`) so a race cannot clobber one either.
- **Secret key file is created owner-only (`0600`)** on POSIX systems, set at
  creation so it is never briefly world-readable. `--force` also tightens an
  existing key file's permissions. (Windows ignores most mode bits.)
- The CLI rejects empty messages and `--output` / `--key-file` pointing at the
  same file.

### Fixed — robustness and security
- **Layout sequence length is now bounded when reading puzzles** (2 to 9
  layouts, i.e. at most 8 transitions, matching what the generator can produce).
  Previously a crafted file could list an arbitrarily long sequence and force
  excessive work before authentication failed.
- **Puzzle `version` must be an actual integer.** `true` and `2.0` compare equal
  to `1`/`2` in Python and were passing the version check.
- `solve_puzzle` rejects non-object envelopes with a clean `ValueError`; the CLI
  reports non-object puzzle JSON as an error instead of crashing.
- **Korean route has a round-trip safety net.** `detect_text_mode` only selects
  the 2-beolsik route if the keystroke conversion provably round-trips for that
  exact message; otherwise it uses UTF-8. A puzzle that cannot be solved can no
  longer be produced.
- The web API now reports the route the engine actually chose, rather than
  recomputing it separately.
- **Host header parsing** uses a real URL parser; malformed Host values are
  rejected with 403 instead of relying on string splitting.
- **Malformed Origin headers fail closed.** Invalid URLs, embedded credentials,
  paths, queries and fragments are rejected as cross-origin requests instead
  of risking an uncaught parser exception.
- **Flask 3 compatibility:** replaced the removed `JSON_AS_ASCII` config key with
  `app.json.ensure_ascii = False`, so non-ASCII JSON is no longer escaped.
- `MAX_MESSAGE_LENGTH` now lives in one place (`cipher_game.puzzle`) and is
  enforced by the engine, so the CLI shares the web app's 20,000-character limit.
- `generate_layout_sequence` rejects booleans and non-integers.
- CLI accepts key files with a UTF-8 BOM (common when saved from Windows tools);
  the browser key loader does the same.

### Changed — versioning
- The UI previously said "v1.0" while the puzzle format is version 2. The
  application version now comes from a single source, `cipher_game.__version__`
  (rendered into the UI, and returned by `/api/health` along with
  `puzzle_format`).

### Changed — UI and accessibility
- **The "Keep your key safe" warning is no longer hidden on small screens.** The
  side panel previously disappeared at ≤820 px; now only the long pipeline
  preview is hidden and the warning stays. The Settings security notes also
  remain visible on mobile.
- **Minimum text size raised to 11 px** (was as low as 7–8 px) and extreme
  letter-spacing capped at 1.2 px. The secondary-text colour was adjusted in both
  themes (about 3.7:1 → 5.3:1 dark, 3.2:1 → 5.5:1 light, against the 4.5:1 WCAG AA
  minimum) and the light-theme key callout text was darkened.
- **Theme follows the system (`prefers-color-scheme`)** until the user chooses one.
  Defaults are no longer written to `localStorage` at startup, only real choices.
- Added `prefers-reduced-motion` support.
- Decorative glyph icons are hidden from screen readers (`aria-hidden`); form
  selects have accessible labels; the mobile menu exposes `aria-expanded` and
  closes with Escape.
- The hidden file inputs are now keyboard-operable (Tab to the drop zone / "Choose
  key file" control, Enter or Space to open the picker).
- The key text box is cleared on page hide, and re-selecting the same file after
  editing it now works.
- Removed an unused `dataset.step` assignment in the Explorer.

### Added — tests (20 → 69 test methods)
- **Exhaustive Hangul coverage:** all 11,172 syllables individually, a spread of
  adjacent-syllable pairs, and a full sweep of final consonant × next initial ×
  next vowel boundaries (where keystroke ambiguity would appear), plus spaces.
- Engine: tampered `puzzle_text`/nonce, wrong-length nonce, missing fields,
  non-integer versions, non-object envelopes, over-long layout sequences (read
  and create), size limits, generator bounds and invariants, and a hand-built
  **legacy v1 puzzle** to guard backward compatibility.
- **New `tests/test_cli.py`:** round trips, refuse-to-overwrite, no partial
  output, `--force`, key-file permissions, same-path rejection, empty message,
  wrong key / tampered puzzle (exit code 2), malformed JSON, BOM keys.
- Web API: Origin rejection (foreign, different port, wrong scheme, `null`) and
  same-origin acceptance, Host allow-list (including look-alike hosts), boolean /
  string / out-of-range `transitions`, oversized message and 413 body, non-object
  JSON bodies, malformed decrypt inputs, tampered envelopes, security headers
  (CSP has no `unsafe-inline`/`unsafe-eval`), no CORS headers, `no-store`, and
  that the key never appears in the envelope.

### Changed — project
- CI now runs on Ubuntu, Windows and macOS across Python 3.10–3.13, with pip
  caching, an explicitly selected Node.js version, read-only repository
  permissions and a job timeout. Python 3.10 or newer is the supported baseline.
- README rewritten: macOS/Linux setup, CLI overwrite behaviour, versioning,
  known limitations and a clearer security section.
- `.gitignore` now also ignores `recovered-message.txt`.

### Known limitations (intentionally unchanged)
These are design decisions rather than bugs, left alone so this release stays a
stable base. See the README for details.
- Keyboard layouts are applied to ciphertext and the layout sequence is stored in
  the puzzle JSON, so the puzzle layers add no difficulty or security.
- The Korean route only triggers for Hangul-and-spaces-only messages.
- No license has been selected.

## [1.0.0]
- Initial release: AES-256-GCM puzzle engine, Korean 2-beolsik and UTF-8 routes,
  QWERTY/Dvorak/AZERTY transformations, CLI, and local Flask browser interface.
