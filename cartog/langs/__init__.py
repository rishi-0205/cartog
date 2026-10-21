"""Language adapter registry and source file parsing coordinator."""

from pathlib import Path
from typing import Optional

from cartog.cache import ParseCache
from cartog.langs.base import LanguageAdapter, ParseFileResult
from cartog.langs.python_adapter import PythonAdapter
from cartog.scan import FileInfo

_ADAPTERS: dict[str, LanguageAdapter] = {}


def _init_adapters():
    if not _ADAPTERS:
        _ADAPTERS["python"] = PythonAdapter()


def get_adapter(name: str) -> Optional[LanguageAdapter]:
    """Retrieve an adapter by language name."""
    _init_adapters()
    return _ADAPTERS.get(name.lower())


def get_adapter_for_path(path: str | Path) -> Optional[LanguageAdapter]:
    """Retrieve the appropriate adapter for a file path based on its extension."""
    _init_adapters()
    p = Path(path)
    suffix = p.suffix.lower()
    for adapter in _ADAPTERS.values():
        if suffix in adapter.extensions:
            return adapter
    return None


def parse_source_file(
    file_info: FileInfo, cache: Optional[ParseCache] = None
) -> ParseFileResult:
    """Parse a source file with tree-sitter, using the cache when available."""
    adapter = get_adapter(file_info.language)
    if not adapter:
        return ParseFileResult(
            path=file_info.path,
            language=file_info.language,
            hash=file_info.sha1,
            has_error=True,
        )

    # 1. Check cache
    if cache is not None:
        cached = cache.get(file_info.sha1, adapter.version)
        if cached is not None:
            # Reconstruct ParseFileResult from cached dict
            symbols = []
            from cartog.langs.base import SymbolRecord, ImportRecord
            for s in cached.get("symbols", []):
                rng = s.get("range", [0, 0, 0, 0])
                symbols.append(
                    SymbolRecord(
                        kind=s["kind"],
                        name=s["name"],
                        qualified_name=s["qualified_name"],
                        start_line=rng[0],
                        start_col=rng[1],
                        end_line=rng[2],
                        end_col=rng[3],
                        parent=s.get("parent"),
                        attrs=s.get("attrs", {}),
                    )
                )
            imports = []
            for i in cached.get("imports", []):
                imports.append(
                    ImportRecord(
                        specifier=i.get("specifier", ""),
                        names=i.get("names", []),
                        aliases=i.get("aliases", {}),
                        kind=i.get("kind", "standard"),
                        line=i.get("line", 0),
                        level=i.get("level", 0),
                        raw_text=i.get("raw_text", ""),
                    )
                )
            return ParseFileResult(
                path=file_info.path,
                language=file_info.language,
                hash=file_info.sha1,
                symbols=symbols,
                imports=imports,
                patterns=cached.get("patterns", []),
                has_error=cached.get("has_error", False),
            )

    # 2. Parse from disk
    try:
        with open(file_info.abs_path, "rb") as f:
            source_bytes = f.read()
    except Exception:
        return ParseFileResult(
            path=file_info.path,
            language=file_info.language,
            hash=file_info.sha1,
            has_error=True,
        )

    # Parse with adapter
    if hasattr(adapter, "parse"):
        tree = adapter.parse(source_bytes)
    else:
        grammar = adapter.grammar_for(Path(file_info.path))
        import tree_sitter
        parser = tree_sitter.Parser(grammar)
        tree = parser.parse(source_bytes)

    symbols = adapter.extract_symbols(tree, source_bytes, file_info.path)
    imports = adapter.extract_imports(tree, source_bytes, file_info.path)
    patterns = adapter.extract_patterns(tree, source_bytes, file_info.path)
    has_error = tree.root_node.has_error

    result = ParseFileResult(
        path=file_info.path,
        language=file_info.language,
        hash=file_info.sha1,
        symbols=symbols,
        imports=imports,
        patterns=patterns,
        has_error=has_error,
    )

    # 3. Update cache
    if cache is not None:
        cache.set(file_info.sha1, adapter.version, result.to_dict())

    return result
