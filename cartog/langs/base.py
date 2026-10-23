"""Language Adapter base interface and symbol/import data structures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import tree_sitter


@dataclass
class SymbolRecord:
    """Extracted code symbol (function, method, class)."""
    kind: str                    # "function", "method", "class"
    name: str                    # e.g. "Command", "_split_opt"
    qualified_name: str          # e.g. "click.core.Command", "click.parser._split_opt"
    start_line: int              # 0-indexed line
    start_col: int               # 0-indexed character offset
    end_line: int                # 0-indexed line
    end_col: int                 # 0-indexed character offset
    parent: Optional[str] = None # Name of parent symbol (e.g. class name for methods)
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "range": [self.start_line, self.start_col, self.end_line, self.end_col],
            "parent": self.parent,
            "attrs": self.attrs,
        }


@dataclass
class ImportRecord:
    """Raw import statement record."""
    specifier: str               # e.g. "click.core", ".parser", "os"
    names: list[str] = field(default_factory=list) # e.g. ["Command"], ["*"]
    aliases: dict[str, str] = field(default_factory=dict) # e.g. {"Command": "Cmd"}
    kind: str = "standard"       # "standard", "from", "relative"
    line: int = 0                # 0-indexed line in file
    level: int = 0               # 0 for absolute, 1 for '.', 2 for '..'
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "specifier": self.specifier,
            "names": self.names,
            "aliases": self.aliases,
            "kind": self.kind,
            "line": self.line,
            "level": self.level,
            "raw_text": self.raw_text,
        }


@dataclass
class ParseFileResult:
    """Aggregated tree-sitter parse result for a single source file."""
    path: str
    language: str
    hash: str
    symbols: list[SymbolRecord] = field(default_factory=list)
    imports: list[ImportRecord] = field(default_factory=list)
    patterns: list[dict[str, Any]] = field(default_factory=list)
    has_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "language": self.language,
            "hash": self.hash,
            "has_error": self.has_error,
            "symbols": [s.to_dict() for s in self.symbols],
            "imports": [i.to_dict() for i in self.imports],
            "patterns": self.patterns,
        }


@dataclass
class ProjectContext:
    """Repository-wide context for import and reference resolution."""
    target_path: str = "."
    roots: list[str] = field(default_factory=lambda: ["."])
    all_files: set[str] = field(default_factory=set)
    module_to_file: dict[str, str] = field(default_factory=dict)
    root_to_modules: dict[str, dict[str, str]] = field(default_factory=dict)


class LanguageAdapter(ABC):
    """Abstract Base Class for language-specific tree-sitter adapters."""

    name: str = ""
    extensions: tuple[str, ...] = ()
    version: str = "1.0.0"

    @abstractmethod
    def grammar_for(self, path: Path) -> tree_sitter.Language:
        """Return the loaded tree-sitter Language for this file."""
        pass

    @abstractmethod
    def extract_symbols(self, tree: tree_sitter.Tree, source_bytes: bytes, path: str) -> list[SymbolRecord]:
        """Extract function, method, and class declarations from the AST."""
        pass

    @abstractmethod
    def extract_imports(self, tree: tree_sitter.Tree, source_bytes: bytes, path: str) -> list[ImportRecord]:
        """Extract raw import statements from the AST."""
        pass

    def extract_patterns(self, tree: tree_sitter.Tree, source_bytes: bytes, path: str) -> list[dict[str, Any]]:
        """Extract framework patterns (routes, CLI commands, entrypoints). Stubs in M1."""
        return []

    def resolve_import(self, record: ImportRecord, from_file: str, project_context: Any) -> str:
        """Resolve an import record to a repo file, external package, or unresolved. Stubs in M1."""
        return "unresolved"

    def detect_roots(self, repo_path: Path) -> list[str]:
        """Detect project roots for this language."""
        return ["."]

    def scip_command(self, root: str, out_path: str) -> tuple[list[str], dict[str, str]]:
        """Return indexer shell command and environment. Stubs in M1."""
        return [], {}
