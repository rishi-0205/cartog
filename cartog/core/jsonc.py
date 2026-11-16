"""JSONC (JSON with Comments) string-aware tokenizer and robust JSON loader.

Handles:
- UTF-8 and UTF-8-SIG (BOM)
- Single-line comments (// ...) outside string literals
- Multi-line block comments (/* ... */) outside string literals
- Preserves newlines so error line numbers remain accurate
- Detects unterminated block comments and raises descriptive errors
- Strips trailing commas before } and ] outside string literals
- Preserves strings containing comment-like sequences (e.g. "src/**/*", "@/*", URLs)
"""

import json
import sys
from pathlib import Path
from typing import Any

from cartog.core.diagnostics import warn


class JsoncParseError(ValueError):
    """Raised when JSONC comment stripping or JSON parsing fails."""
    pass


def strip_jsonc_comments_and_trailing_commas(text: str, filename: str = "<string>") -> str:
    """Strip // and /* */ comments and trailing commas outside string literals.
    
    Preserves all newline characters so downstream json.loads line numbers match source.
    Raises JsoncParseError on unterminated block comments.
    """
    # Accept UTF-8 BOM if present
    if text.startswith("\ufeff"):
        text = text[1:]

    out: list[str] = []
    n = len(text)
    i = 0
    in_string = False
    escape = False

    while i < n:
        c = text[i]

        if in_string:
            out.append(c)
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            i += 1
        else:
            # Outside string literal
            if c == '"':
                in_string = True
                out.append(c)
                i += 1
            elif c == "/" and i + 1 < n and text[i + 1] == "/":
                # Single line comment: consume until \n or EOF
                i += 2
                while i < n and text[i] != "\n":
                    i += 1
                if i < n and text[i] == "\n":
                    out.append("\n")
                    i += 1
            elif c == "/" and i + 1 < n and text[i + 1] == "*":
                # Block comment: consume until */
                comment_start_line = "".join(out).count("\n") + 1
                i += 2
                terminated = False
                while i + 1 < n:
                    if text[i] == "*" and text[i + 1] == "/":
                        terminated = True
                        i += 2
                        break
                    if text[i] == "\n":
                        out.append("\n")  # Preserve newline count
                    i += 1
                if not terminated:
                    msg = f"Unterminated block comment in '{filename}' starting at line {comment_start_line}"
                    warn(msg, stacklevel=3)
                    raise JsoncParseError(msg)
            elif c == ",":
                # Check for trailing comma before } or ]
                j = i + 1
                is_trailing = False
                while j < n:
                    cj = text[j]
                    if cj in " \t\r\n":
                        j += 1
                    elif cj == "/" and j + 1 < n and text[j + 1] == "/":
                        # Comment line in lookahead
                        j += 2
                        while j < n and text[j] != "\n":
                            j += 1
                    elif cj == "/" and j + 1 < n and text[j + 1] == "*":
                        # Comment block in lookahead
                        j += 2
                        while j + 1 < n and not (text[j] == "*" and text[j + 1] == "/"):
                            j += 1
                        j += 2
                    else:
                        if cj in "}]":
                            is_trailing = True
                        break
                if not is_trailing:
                    out.append(c)
                i += 1
            else:
                out.append(c)
                i += 1

    return "".join(out)


def load_jsonc_file(
    path: Path | str,
    project_context: Any | None = None,
) -> dict[str, Any] | None:
    """Load and parse a JSONC file (tsconfig.json, jsconfig.json) tolerating comments and trailing commas.
    
    Reads file using utf-8-sig encoding.
    Never fails silently: on error, records a warning in project_context if provided,
    prints a one-line notice to stderr, and returns None.
    """
    p = Path(path)
    if not p.is_file():
        return None

    try:
        raw = p.read_text(encoding="utf-8-sig")
    except Exception as e:
        msg = f"Failed to read '{p.as_posix()}': {e}"
        print(f"Warning: {msg}", file=sys.stderr)
        if project_context and hasattr(project_context, "config_warnings"):
            project_context.config_warnings.append({"file": p.as_posix(), "error": str(e)})
        return None

    try:
        clean = strip_jsonc_comments_and_trailing_commas(raw, filename=p.as_posix())
        return json.loads(clean)
    except Exception as e:
        msg = f"Failed to parse JSONC '{p.as_posix()}': {e}"
        print(f"Warning: {msg}", file=sys.stderr)
        if project_context and hasattr(project_context, "config_warnings"):
            project_context.config_warnings.append({"file": p.as_posix(), "error": str(e)})
        return None


def load_strict_json_file(
    path: Path | str,
    project_context: Any | None = None,
) -> dict[str, Any] | None:
    """Load and parse strict JSON file (package.json) using standard json.loads and utf-8-sig.
    
    Never fails silently: on error, records a warning in project_context if provided,
    prints a one-line notice to stderr, and returns None.
    """
    p = Path(path)
    if not p.is_file():
        return None

    try:
        raw = p.read_text(encoding="utf-8-sig")
    except Exception as e:
        msg = f"Failed to read '{p.as_posix()}': {e}"
        print(f"Warning: {msg}", file=sys.stderr)
        if project_context and hasattr(project_context, "config_warnings"):
            project_context.config_warnings.append({"file": p.as_posix(), "error": str(e)})
        return None

    try:
        return json.loads(raw)
    except Exception as e:
        msg = f"Failed to parse strict JSON '{p.as_posix()}': {e}"
        print(f"Warning: {msg}", file=sys.stderr)
        if project_context and hasattr(project_context, "config_warnings"):
            project_context.config_warnings.append({"file": p.as_posix(), "error": str(e)})
        return None
