"""CipherKeys: an educational layered cryptographic puzzle."""

from .crypto import generate_key, key_from_text, key_to_text
from .puzzle import create_puzzle, solve_puzzle

# Application release version (shown in the UI and /api/health).
# This is separate from the puzzle *file format* version, `puzzle.VERSION`,
# which only changes when the JSON envelope format changes.
__version__ = "1.1.0"

__all__ = [
    "__version__",
    "generate_key",
    "key_from_text",
    "key_to_text",
    "create_puzzle",
    "solve_puzzle",
]
