"""Sanitizers for text that reaches a terminal or a plain-text document (S6).

Untrusted names, paths, and error strings can carry ANSI escape sequences
(``ESC [ 31 m``), OSC titles (``ESC ] 0 ; ... BEL``), or raw C0/C1 control
characters. Rendering them verbatim lets a crafted repository rewrite the
operator's terminal. Everything printed through :mod:`cartog.cli.shared` and
every digest goes through :func:`sanitize_console_text` first.
"""

from __future__ import annotations

import re

#: Complete ANSI escape sequences: CSI, OSC (BEL- or ST-terminated), and the
#: two-byte forms. Strip the whole sequence, not just the ESC byte, so the
#: parameter/terminator bytes do not survive as visible junk.
_ANSI_SEQUENCES = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"  # CSI ... final byte
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC ... BEL or ST
    r"|\x1b[@-_]"  # two-byte escape
)

#: C0 controls except TAB (0x09) and LF (0x0A), DEL, and the C1 block.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def sanitize_console_text(text: object) -> str:
    """Return ``text`` with ANSI sequences and control characters removed.

    Newline and tab are preserved because they are ordinary layout in console
    and Markdown output; carriage return is removed so a hostile name cannot
    overwrite the line just printed.
    """
    cleaned = _ANSI_SEQUENCES.sub("", str(text))
    return _CONTROL_CHARS.sub("", cleaned)
