"""Reversible keyboard-layout transformations used as puzzle mechanics."""

from __future__ import annotations

import secrets

# Labels at the 26 physical positions occupied by letters on QWERTY.
# Some target positions become punctuation on Dvorak/AZERTY. They remain
# reversible because each layout is represented by a one-to-one mapping.
_LAYOUT_ROWS = {
    "qwerty": "qwertyuiopasdfghjklzxcvbnm",
    "dvorak": "',.pyfgcrlaoeuidhtn;qjkxbm",
    "azerty": "azertyuiopqsdfghjklwxcvbn,",
}

for _name, _labels in _LAYOUT_ROWS.items():
    if len(_labels) != 26 or len(set(_labels)) != 26:
        raise RuntimeError(f"Invalid keyboard layout definition: {_name}")

LAYOUTS = tuple(_LAYOUT_ROWS)


def transform_layout(text: str, source: str, target: str) -> str:
    """Relabel physical keys from one layout to another."""
    if source not in _LAYOUT_ROWS or target not in _LAYOUT_ROWS:
        raise ValueError("Unknown keyboard layout.")
    translation = dict(zip(_LAYOUT_ROWS[source], _LAYOUT_ROWS[target]))
    return "".join(translation.get(char, char) for char in text)


def generate_layout_sequence(transitions: int | None = None) -> list[str]:
    """Create a random layout sequence beginning at QWERTY."""
    if transitions is None:
        transitions = 2 + secrets.randbelow(3)  # 2 to 4 transitions
    if not 1 <= transitions <= 8:
        raise ValueError("transitions must be between 1 and 8")

    sequence = ["qwerty"]
    for _ in range(transitions):
        choices = [layout for layout in LAYOUTS if layout != sequence[-1]]
        sequence.append(secrets.choice(choices))
    return sequence


def apply_layout_sequence(text: str, sequence: list[str]) -> str:
    if len(sequence) < 2:
        raise ValueError("A layout sequence must contain at least two layouts.")
    result = text
    for source, target in zip(sequence, sequence[1:]):
        result = transform_layout(result, source, target)
    return result


def reverse_layout_sequence(text: str, sequence: list[str]) -> str:
    if len(sequence) < 2:
        raise ValueError("A layout sequence must contain at least two layouts.")
    result = text
    for source, target in reversed(list(zip(sequence, sequence[1:]))):
        result = transform_layout(result, target, source)
    return result
