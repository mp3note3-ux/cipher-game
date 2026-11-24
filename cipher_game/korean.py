"""Korean Hangul <-> standard 2-beolsik keyboard conversion.

This first version supports precomposed Hangul syllables and spaces.
The conversion is a puzzle transformation, not encryption.
"""

from __future__ import annotations

S_BASE = 0xAC00
L_COUNT = 19
V_COUNT = 21
T_COUNT = 28
N_COUNT = V_COUNT * T_COUNT
S_COUNT = L_COUNT * N_COUNT

INITIALS = [
    "ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ",
]
VOWELS = [
    "ㅏ", "ㅐ", "ㅑ", "ㅒ", "ㅓ", "ㅔ", "ㅕ", "ㅖ", "ㅗ", "ㅘ",
    "ㅙ", "ㅚ", "ㅛ", "ㅜ", "ㅝ", "ㅞ", "ㅟ", "ㅠ", "ㅡ", "ㅢ", "ㅣ",
]
FINALS = [
    "", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ",
    "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ",
    "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ",
]

INITIAL_TO_KEY = dict(zip(INITIALS, [
    "r", "R", "s", "e", "E", "f", "a", "q", "Q", "t",
    "T", "d", "w", "W", "c", "z", "x", "v", "g",
]))
VOWEL_TO_KEYS = {
    "ㅏ": "k", "ㅐ": "o", "ㅑ": "i", "ㅒ": "O", "ㅓ": "j",
    "ㅔ": "p", "ㅕ": "u", "ㅖ": "P", "ㅗ": "h", "ㅘ": "hk",
    "ㅙ": "ho", "ㅚ": "hl", "ㅛ": "y", "ㅜ": "n", "ㅝ": "nj",
    "ㅞ": "np", "ㅟ": "nl", "ㅠ": "b", "ㅡ": "m", "ㅢ": "ml",
    "ㅣ": "l",
}
FINAL_TO_KEYS = {
    "": "", "ㄱ": "r", "ㄲ": "R", "ㄳ": "rt", "ㄴ": "s",
    "ㄵ": "sw", "ㄶ": "sg", "ㄷ": "e", "ㄹ": "f", "ㄺ": "fr",
    "ㄻ": "fa", "ㄼ": "fq", "ㄽ": "ft", "ㄾ": "fx", "ㄿ": "fv",
    "ㅀ": "fg", "ㅁ": "a", "ㅂ": "q", "ㅄ": "qt", "ㅅ": "t",
    "ㅆ": "T", "ㅇ": "d", "ㅈ": "w", "ㅊ": "c", "ㅋ": "z",
    "ㅌ": "x", "ㅍ": "v", "ㅎ": "g",
}

KEY_TO_INITIAL = {key: jamo for jamo, key in INITIAL_TO_KEY.items()}
KEYS_TO_VOWEL = {keys: jamo for jamo, keys in VOWEL_TO_KEYS.items()}
KEY_TO_FINAL = {keys: jamo for jamo, keys in FINAL_TO_KEYS.items() if keys}
VOWEL_KEYS = set("koijup hnybml".replace(" ", "")) | {"O", "P"}
CONSONANT_KEYS = set(KEY_TO_INITIAL)


def hangul_to_2beolsik(text: str) -> str:
    """Convert precomposed Hangul syllables to 2-beolsik keystrokes."""
    output: list[str] = []
    for char in text:
        if char == " ":
            output.append(char)
            continue
        code = ord(char)
        if not (S_BASE <= code < S_BASE + S_COUNT):
            raise ValueError(
                f"Unsupported character {char!r}; this version accepts "
                "precomposed Hangul syllables and spaces only."
            )
        syllable_index = code - S_BASE
        initial_index = syllable_index // N_COUNT
        vowel_index = (syllable_index % N_COUNT) // T_COUNT
        final_index = syllable_index % T_COUNT
        output.append(INITIAL_TO_KEY[INITIALS[initial_index]])
        output.append(VOWEL_TO_KEYS[VOWELS[vowel_index]])
        output.append(FINAL_TO_KEYS[FINALS[final_index]])
    return "".join(output)


def keys_to_hangul(keys: str) -> str:
    """Compose standard 2-beolsik keystrokes into precomposed Hangul."""
    output: list[str] = []
    i = 0
    vowel_keys_sorted = sorted(KEYS_TO_VOWEL, key=len, reverse=True)

    while i < len(keys):
        if keys[i] == " ":
            output.append(" ")
            i += 1
            continue

        initial = KEY_TO_INITIAL.get(keys[i])
        if initial is None:
            raise ValueError(f"Expected an initial consonant at position {i}.")
        i += 1

        vowel = None
        vowel_length = 0
        for candidate in vowel_keys_sorted:
            if keys.startswith(candidate, i):
                vowel = KEYS_TO_VOWEL[candidate]
                vowel_length = len(candidate)
                break
        if vowel is None:
            raise ValueError(f"Expected a vowel at position {i}.")
        i += vowel_length

        run_start = i
        while i < len(keys) and keys[i] in CONSONANT_KEYS:
            i += 1
        run = keys[run_start:i]
        has_next_vowel = i < len(keys) and keys[i] in VOWEL_KEYS
        final = ""

        if len(run) == 1:
            if not has_next_vowel:
                final = KEY_TO_FINAL[run]
                i = run_start + 1
            else:
                i = run_start
        elif len(run) == 2:
            pair_final = KEY_TO_FINAL.get(run)
            if has_next_vowel:
                final = KEY_TO_FINAL.get(run[0], "")
                if not final:
                    raise ValueError("Invalid final consonant.")
                i = run_start + 1
            elif pair_final:
                final = pair_final
                i = run_start + 2
            else:
                raise ValueError("Invalid two-key final consonant sequence.")
        elif len(run) >= 3:
            pair_final = KEY_TO_FINAL.get(run[:2])
            if not has_next_vowel or not pair_final:
                raise ValueError("Invalid consonant sequence after a vowel.")
            final = pair_final
            i = run_start + 2

        l_index = INITIALS.index(initial)
        v_index = VOWELS.index(vowel)
        t_index = FINALS.index(final)
        output.append(chr(S_BASE + (l_index * V_COUNT + v_index) * T_COUNT + t_index))

    return "".join(output)
