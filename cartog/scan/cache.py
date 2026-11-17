"""Content-hash based AST parse cache."""

import json
from pathlib import Path
from typing import Any

from cartog import __version__ as CARTOG_VERSION

__all__ = ["DEFAULT_EXTRACTOR_SCHEMA_VERSION", "ParseCache"]

DEFAULT_EXTRACTOR_SCHEMA_VERSION = f"cartog-v{CARTOG_VERSION}-m10"


class ParseCache:
    """Manages disk caching of per-file tree-sitter AST parse results."""

    def __init__(
        self,
        cache_dir: str | Path,
        schema_version: str | None = None,
        ignore_hash: str | None = None,
        force: bool = False,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "cache.json"
        self.schema_version = schema_version or DEFAULT_EXTRACTOR_SCHEMA_VERSION
        self.ignore_hash = ignore_hash or "none"
        self.force = force
        self._entries: dict[str, Any] = {}
        self._dirty = False
        self.hits = 0
        self.misses = 0
        self.load()

    def _make_key(self, file_sha1: str, adapter_version: str) -> str:
        return f"{self.schema_version}:{self.ignore_hash}:{file_sha1}:{adapter_version}"

    def load(self) -> None:
        """Load cache entries from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._entries = data
            except Exception as e:
                import sys
                print(f"Warning: Failed to load cache at '{self.cache_file}': {e}", file=sys.stderr)
                # If cache is corrupted, start fresh
                self._entries = {}

    def clear(self) -> None:
        """Clear all in-memory and on-disk cache entries."""
        self._entries = {}
        self._dirty = False
        if self.cache_file.exists():
            try:
                self.cache_file.unlink()
            except Exception:
                pass

    def get(self, file_sha1: str, adapter_version: str) -> dict[str, Any] | None:
        """Retrieve cached parse result for a file hash and adapter version."""
        if self.force:
            self.misses += 1
            return None
        key = self._make_key(file_sha1, adapter_version)
        entry = self._entries.get(key)
        if entry is not None:
            self.hits += 1
            return entry
        self.misses += 1
        return None

    def set(self, file_sha1: str, adapter_version: str, data: dict[str, Any]) -> None:
        """Cache parse result for a file hash."""
        key = self._make_key(file_sha1, adapter_version)
        self._entries[key] = data
        self._dirty = True

    def save(self) -> None:
        """Persist dirty cache entries to disk."""
        if not self._dirty:
            return
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, indent=2)
            self._dirty = False
        except Exception:
            # Disk write failure should fail soft
            pass
