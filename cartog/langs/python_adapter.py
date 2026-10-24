"""Python Language Adapter using tree-sitter-python and tree-sitter Query."""

import ast
from pathlib import Path
import re
from typing import Any, NamedTuple, Optional
import tree_sitter
import tree_sitter_python

from cartog.langs.base import (
    ImportRecord,
    LanguageAdapter,
    ProjectContext,
    SymbolRecord,
)


SYMBOL_QUERY = """
(class_definition
  name: (identifier) @name) @class

(function_definition
  name: (identifier) @name) @func
"""

DECORATOR_QUERY = """
(decorated_definition
  (decorator)+ @decorator
  definition: [
    (function_definition)
    (class_definition)
  ] @target)
"""

IMPORT_QUERY = """
(import_statement) @import
(import_from_statement) @import_from
"""

PATTERN_QUERY = """
(decorated_definition
  (decorator) @decorator
  definition: (function_definition
    name: (identifier) @func_name) @func)

(if_statement
  condition: (_) @cond
  consequence: (_) @body) @if_stmt
"""


def parse_route_decorator(dec_text: str) -> Optional[dict[str, Any]]:
    """Parse Flask or FastAPI route decorator to extract HTTP methods and URL path."""
    text = dec_text.lstrip("@").strip()
    route_match = re.search(r'\.(route|get|post|put|delete|patch)\s*\((.*)\)', text, re.DOTALL)
    if not route_match:
        return None
    method_kind = route_match.group(1).lower()
    args_str = route_match.group(2).strip()

    url_path = "/"
    methods = []
    try:
        parsed_call = ast.parse(f"f({args_str})").body[0].value
        if parsed_call.args:
            first_arg = parsed_call.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                url_path = first_arg.value
        if method_kind != "route":
            methods = [method_kind.upper()]
        else:
            for kw in parsed_call.keywords:
                if kw.arg == "methods":
                    if isinstance(kw.value, (ast.List, ast.Tuple, ast.Set)):
                        methods = [
                            elt.value for elt in kw.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        ]
            if not methods:
                methods = ["GET"]
    except Exception:
        p_match = re.search(r'["\']([^"\']+)["\']', args_str)
        if p_match:
            url_path = p_match.group(1)
        methods = [method_kind.upper()] if method_kind != "route" else ["GET"]

    return {
        "url_path": url_path,
        "methods": methods,
        "name": f"{', '.join(methods)} {url_path}",
    }


def parse_command_decorator(dec_text: str, default_name: str) -> Optional[dict[str, Any]]:
    """Parse Click command or group decorator to extract CLI command name and group status."""
    text = dec_text.lstrip("@").strip()
    is_group = ".group" in text or text.startswith("group")
    is_command = ".command" in text or text.startswith("command") or "click.command" in text or "click.group" in text
    if not (is_group or is_command):
        return None

    cmd_name = default_name.replace("_", "-")
    try:
        call_str = text if "(" in text else f"{text}()"
        parsed_call = ast.parse(call_str).body[0].value
        if hasattr(parsed_call, "args") and parsed_call.args:
            first = parsed_call.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                cmd_name = first.value
        if hasattr(parsed_call, "keywords"):
            for kw in parsed_call.keywords:
                if kw.arg == "name" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    cmd_name = kw.value.value
    except Exception:
        pass

    return {
        "command_name": cmd_name,
        "is_group": is_group,
    }


class ScopeEntry(NamedTuple):
    name: str
    end_byte: int
    is_class: bool


def get_enclosing_root(rel_path: str, roots: list[str]) -> str:
    """Find the nearest enclosing project root for a repo-relative file path."""
    p_str = rel_path.replace("\\", "/")
    matching = []
    for r in roots:
        r_norm = r.replace("\\", "/").rstrip("/")
        if r_norm == "." or not r_norm:
            matching.append((".", 0))
        elif p_str == r_norm or p_str.startswith(r_norm + "/"):
            matching.append((r_norm, len(r_norm)))
    if not matching:
        return "."
    matching.sort(key=lambda x: x[1], reverse=True)
    return matching[0][0]


def path_to_module_name(
    rel_path: str,
    roots: Optional[list[str]] = None,
    all_files: Optional[set[str]] = None,
) -> str:
    """Convert a repo-relative path into a Python module name relative to its enclosing root and source folder."""
    p_str = rel_path.replace("\\", "/")
    roots_list = roots or ["."]
    enc_root = get_enclosing_root(p_str, roots_list)

    if enc_root == "." or not enc_root:
        subpath = p_str
    elif p_str.startswith(enc_root + "/"):
        subpath = p_str[len(enc_root) + 1 :]
    else:
        subpath = p_str

    parts = list(Path(subpath).parts)
    if parts and parts[0] in ("src", "lib"):
        parts = parts[1:]
    if not parts:
        return ""

    last = parts[-1]
    if last.endswith(".py"):
        last = last[:-3]
    elif last.endswith(".pyi"):
        last = last[:-4]
    if last == "__init__":
        parts = parts[:-1]
    else:
        parts[-1] = last
    return ".".join(parts)


class PythonAdapter(LanguageAdapter):
    """Tree-sitter adapter for Python source code using native queries."""

    name = "python"
    extensions = (".py", ".pyi")
    version = "1.1.0"

    def __init__(self):
        self._language = tree_sitter.Language(tree_sitter_python.language())
        self._parser = tree_sitter.Parser(self._language)
        # Precompile tree-sitter queries for maximum performance
        self._query_symbols = tree_sitter.Query(self._language, SYMBOL_QUERY)
        self._query_decorators = tree_sitter.Query(self._language, DECORATOR_QUERY)
        self._query_imports = tree_sitter.Query(self._language, IMPORT_QUERY)
        self._query_patterns = tree_sitter.Query(self._language, PATTERN_QUERY)

    def grammar_for(self, path: Path) -> tree_sitter.Language:
        return self._language

    def parse(self, source_bytes: bytes) -> tree_sitter.Tree:
        return self._parser.parse(source_bytes)

    def extract_symbols(
        self, tree: tree_sitter.Tree, source_bytes: bytes, path: str
    ) -> list[SymbolRecord]:
        """Extract functions, classes, and methods with qualified names and source ranges via queries."""
        module_name = path_to_module_name(path)
        symbols: list[SymbolRecord] = []

        def _get_node_text(node: tree_sitter.Node) -> str:
            return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

        # 1. Map target spans to decorator names using native query
        cursor_dec = tree_sitter.QueryCursor(self._query_decorators)
        decorators_by_target: dict[tuple[int, int], list[str]] = {}
        for pat_idx, match in cursor_dec.matches(tree.root_node):
            for target in match.get("target", []):
                key = (target.start_byte, target.end_byte)
                if key not in decorators_by_target:
                    decorators_by_target[key] = []
                for d in match.get("decorator", []):
                    d_text = _get_node_text(d).strip()
                    if d_text.startswith("@"):
                        d_text = d_text[1:].strip()
                    if d_text not in decorators_by_target[key]:
                        decorators_by_target[key].append(d_text)

        # 2. Extract symbols in document order using native query
        cursor_sym = tree_sitter.QueryCursor(self._query_symbols)
        scope_stack: list[ScopeEntry] = []

        for pat_idx, match in cursor_sym.matches(tree.root_node):
            is_class = "class" in match
            node = match["class"][0] if is_class else match["func"][0]
            name_node = match["name"][0]
            name = _get_node_text(name_node)

            # Pop finished scopes
            while scope_stack and node.start_byte >= scope_stack[-1].end_byte:
                scope_stack.pop()

            # Immediate parent class for methods
            parent_class: Optional[str] = None
            if scope_stack and scope_stack[-1].is_class:
                parent_class = scope_stack[-1].name

            # Determine kind
            if is_class:
                kind = "class"
            elif parent_class is not None:
                kind = "method"
            else:
                kind = "function"

            # Build qualified name
            qname_parts = [module_name] if module_name else []
            for entry in scope_stack:
                qname_parts.append(entry.name)
            qname_parts.append(name)
            qname = ".".join(qname_parts)

            # Check async: in Python grammar, async functions begin with 'async '
            is_async = False
            if not is_class:
                prefix = source_bytes[node.start_byte:min(node.start_byte + 7, len(source_bytes))]
                is_async = prefix.startswith(b"async ")

            decorators = decorators_by_target.get((node.start_byte, node.end_byte), [])
            attrs: dict[str, Any] = {}
            if decorators:
                attrs["decorators"] = decorators
            if is_async:
                attrs["async"] = True

            sym = SymbolRecord(
                kind=kind,
                name=name,
                qualified_name=qname,
                start_line=node.start_point.row + 1,
                start_col=node.start_point.column,
                end_line=node.end_point.row + 1,
                end_col=node.end_point.column,
                parent=parent_class,
                attrs=attrs,
            )
            symbols.append(sym)

            # Push to scope stack
            scope_stack.append(ScopeEntry(name=name, end_byte=node.end_byte, is_class=is_class))

        # Sort symbols deterministically by start position
        symbols.sort(key=lambda s: (s.start_line, s.start_col, s.name))
        return symbols

    def extract_imports(
        self, tree: tree_sitter.Tree, source_bytes: bytes, path: str
    ) -> list[ImportRecord]:
        """Extract raw import statements without attempting filesystem resolution via queries."""
        imports: list[ImportRecord] = []

        def _get_node_text(node: tree_sitter.Node) -> str:
            return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

        cursor_imp = tree_sitter.QueryCursor(self._query_imports)
        for pat_idx, match in cursor_imp.matches(tree.root_node):
            if "import" in match:
                node = match["import"][0]
                raw_text = _get_node_text(node).strip()
                line = node.start_point.row

                for child in node.children:
                    if child.type == "dotted_name":
                        spec = _get_node_text(child).strip()
                        imports.append(
                            ImportRecord(
                                specifier=spec,
                                names=[],
                                aliases={},
                                kind="standard",
                                line=line,
                                level=0,
                                raw_text=raw_text,
                            )
                        )
                    elif child.type == "aliased_import":
                        name_child = child.child_by_field_name("name")
                        alias_child = child.child_by_field_name("alias")
                        if name_child and alias_child:
                            spec = _get_node_text(name_child).strip()
                            alias = _get_node_text(alias_child).strip()
                            imports.append(
                                ImportRecord(
                                    specifier=spec,
                                    names=[],
                                    aliases={spec: alias},
                                    kind="standard",
                                    line=line,
                                    level=0,
                                    raw_text=raw_text,
                                )
                            )

            elif "import_from" in match:
                node = match["import_from"][0]
                raw_text = _get_node_text(node).strip()
                line = node.start_point.row

                module_name = ""
                level = 0
                names: list[str] = []
                aliases: dict[str, str] = {}
                mod_child = node.child_by_field_name("module_name")

                # Look for relative_import or import_prefix
                rel_node = None
                for child in node.children:
                    if child.type == "relative_import":
                        rel_node = child
                        break
                    elif child.type == "import_prefix":
                        level += len(_get_node_text(child))

                if rel_node:
                    for c in rel_node.children:
                        if c.type == "import_prefix":
                            level += len(_get_node_text(c))
                        elif c.type == "dotted_name":
                            module_name = _get_node_text(c).strip()
                elif mod_child and mod_child.type == "dotted_name":
                    module_name = _get_node_text(mod_child).strip()

                # Extract imported names
                for child in node.children:
                    if child.type == "wildcard_import":
                        names.append("*")
                    elif child.type == "dotted_name" and child != mod_child:
                        names.append(_get_node_text(child).strip())
                    elif child.type == "aliased_import":
                        n_c = child.child_by_field_name("name")
                        a_c = child.child_by_field_name("alias")
                        if n_c and a_c:
                            n = _get_node_text(n_c).strip()
                            a = _get_node_text(a_c).strip()
                            names.append(n)
                            aliases[n] = a

                kind = "relative" if level > 0 else "from"
                imports.append(
                    ImportRecord(
                        specifier=module_name,
                        names=names,
                        aliases=aliases,
                        kind=kind,
                        line=line,
                        level=level,
                        raw_text=raw_text,
                    )
                )

        # Sort imports deterministically by line number and specifier
        imports.sort(key=lambda i: (i.line, i.specifier))
        return imports

    def extract_patterns(
        self, tree: tree_sitter.Tree, source_bytes: bytes, path: str
    ) -> list[dict[str, Any]]:
        """Extract framework patterns: routes, CLI commands, entrypoints."""
        patterns: list[dict[str, Any]] = []
        cursor = tree_sitter.QueryCursor(self._query_patterns)

        for pat_idx, match in cursor.matches(tree.root_node):
            if "decorator" in match and "func_name" in match:
                dec_node = match["decorator"][0]
                func_node = match["func_name"][0]
                dec_text = source_bytes[dec_node.start_byte:dec_node.end_byte].decode("utf-8", errors="ignore").strip()
                func_name = source_bytes[func_node.start_byte:func_node.end_byte].decode("utf-8", errors="ignore").strip()

                route_info = parse_route_decorator(dec_text)
                if route_info:
                    patterns.append(
                        {
                            "kind": "route",
                            "name": route_info["name"],
                            "url_path": route_info["url_path"],
                            "methods": route_info["methods"],
                            "handler": func_name,
                            "range": [
                                dec_node.start_point.row + 1,
                                dec_node.start_point.column,
                                dec_node.end_point.row + 1,
                                dec_node.end_point.column,
                            ],
                            "raw_text": dec_text,
                        }
                    )

                cmd_info = parse_command_decorator(dec_text, func_name)
                if cmd_info:
                    patterns.append(
                        {
                            "kind": "command",
                            "name": cmd_info["command_name"],
                            "is_group": cmd_info["is_group"],
                            "handler": func_name,
                            "range": [
                                dec_node.start_point.row + 1,
                                dec_node.start_point.column,
                                dec_node.end_point.row + 1,
                                dec_node.end_point.column,
                            ],
                            "raw_text": dec_text,
                        }
                    )

            elif "if_stmt" in match:
                cond_node = match["cond"][0]
                if_node = match["if_stmt"][0]
                cond_text = source_bytes[cond_node.start_byte:cond_node.end_byte].decode("utf-8", errors="ignore")
                if "__name__" in cond_text and ("'__main__'" in cond_text or '"__main__"' in cond_text):
                    body_node = match.get("body", [None])[0]
                    target_call = None
                    if body_node:
                        body_text = source_bytes[body_node.start_byte:body_node.end_byte].decode("utf-8", errors="ignore")
                        call_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', body_text)
                        if call_match and call_match.group(1) not in ("print", "exit", "sys"):
                            target_call = call_match.group(1)

                    patterns.append(
                        {
                            "kind": "entrypoint",
                            "name": "__main__",
                            "target": target_call,
                            "range": [
                                if_node.start_point.row + 1,
                                if_node.start_point.column,
                                if_node.end_point.row + 1,
                                if_node.end_point.column,
                            ],
                            "raw_text": cond_text.strip(),
                        }
                    )

        # Sort patterns deterministically by line number
        patterns.sort(key=lambda p: (p["range"][0], p["name"]))
        return patterns

    def resolve_import(
        self, record: ImportRecord, from_file: str, project_context: ProjectContext
    ) -> str:
        """Resolve a Python ImportRecord to an internal repo path, external package, or unresolved."""
        # 1. Relative import resolution (level > 0 or kind == "relative")
        if record.level > 0 or record.kind == "relative":
            from_p = Path(from_file).parent
            base_p = from_p
            for _ in range(record.level - 1):
                base_p = base_p.parent

            spec = record.specifier.replace(".", "/") if record.specifier else ""
            target_base = (base_p / spec) if spec else base_p

            # When specifier is empty (e.g. 'from . import utils'), check if names correspond to sibling modules
            if not spec:
                for name in record.names:
                    sub_py = (target_base / f"{name}.py").as_posix()
                    if sub_py in project_context.all_files:
                        return sub_py
                    sub_init = (target_base / name / "__init__.py").as_posix()
                    if sub_init in project_context.all_files:
                        return sub_init

            c_py = target_base.with_suffix(".py").as_posix()
            if c_py in project_context.all_files:
                return c_py
            c_pyi = target_base.with_suffix(".pyi").as_posix()
            if c_pyi in project_context.all_files:
                return c_pyi
            c_init = (target_base / "__init__.py").as_posix()
            if c_init in project_context.all_files:
                return c_init
            c_raw = target_base.as_posix()
            if c_raw in project_context.all_files:
                return c_raw

            for name in record.names:
                sub_py = (target_base / f"{name}.py").as_posix()
                if sub_py in project_context.all_files:
                    return sub_py
                sub_init = (target_base / name / "__init__.py").as_posix()
                if sub_init in project_context.all_files:
                    return sub_init

            return "unresolved"

        # 2. Absolute import resolution
        specifier = record.specifier.strip()
        if not specifier:
            return "unresolved"

        roots = getattr(project_context, "roots", ["."]) or ["."]
        own_root = get_enclosing_root(from_file, roots)
        ordered_roots = [own_root] + [r for r in roots if r != own_root]
        root_to_modules = getattr(project_context, "root_to_modules", {})

        # A. Check roots in order (own root first, then remaining roots)
        for r in ordered_roots:
            # Check module mapping for root r
            r_mods = root_to_modules.get(r, {})
            for name in record.names:
                sub_mod = f"{specifier}.{name}"
                if sub_mod in r_mods:
                    return r_mods[sub_mod]
            if specifier in r_mods:
                return r_mods[specifier]

            # Check filesystem candidates under root r
            r_p = Path(r) if r != "." else Path("")
            search_bases = [r_p / "src", r_p / "lib", r_p]
            spec_rel = specifier.replace(".", "/")

            for base in search_bases:
                for name in record.names:
                    sub_candidates = [
                        (base / spec_rel / f"{name}.py").as_posix().lstrip("/"),
                        (base / spec_rel / name / "__init__.py").as_posix().lstrip("/"),
                    ]
                    for sc in sub_candidates:
                        if sc in project_context.all_files:
                            return sc

                candidates = [
                    (base / f"{spec_rel}.py").as_posix().lstrip("/"),
                    (base / f"{spec_rel}.pyi").as_posix().lstrip("/"),
                    (base / spec_rel / "__init__.py").as_posix().lstrip("/"),
                ]
                for c in candidates:
                    if c in project_context.all_files:
                        return c

        # B. Fallback to global module_to_file if present
        for name in record.names:
            sub_mod = f"{specifier}.{name}"
            if sub_mod in project_context.module_to_file:
                return project_context.module_to_file[sub_mod]
        if specifier in project_context.module_to_file:
            return project_context.module_to_file[specifier]

        # C. External package (stdlib or third-party)
        top_pkg = specifier.split(".")[0]

        # Check if top-level module matches a directory or file name anywhere in the repo
        matched = False
        for af in project_context.all_files:
            for p_part in Path(af).parts:
                if p_part == top_pkg or p_part == f"{top_pkg}.py" or p_part == f"{top_pkg}.pyi":
                    matched = True
                    break
            if matched:
                break

        if matched:
            import logging
            logging.getLogger("cartog").warning(
                f"Import '{record.raw_text or record.specifier}' in '{from_file}' matches repo directory or file '{top_pkg}' but could not be resolved; treating as external."
            )

        return f"external:{top_pkg}"

