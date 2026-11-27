"""Python Language Adapter using tree-sitter-python and tree-sitter Query."""

import ast
import re
from pathlib import Path
from typing import Any, NamedTuple

import tree_sitter
import tree_sitter_python

from cartog.core.diagnostics import get_logger
from cartog.parse.base import (
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


def parse_route_decorator(dec_text: str) -> dict[str, Any] | None:
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


def parse_command_decorator(dec_text: str, default_name: str) -> dict[str, Any] | None:
    """Parse a decorator-based named registration into a command spec.

    Generic structural rule: any decorator that registers a function by name
    (optionally with a string literal name) is a command. No framework names.
    """
    text = dec_text.lstrip("@").strip()
    # Any decorator on a function is a named registration; the name comes from
    # a string literal arg/kwarg, else from the function name.
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
        "is_group": False,
    }


class ScopeEntry(NamedTuple):
    """One lexical scope pushed while scanning Python source."""
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
    roots: list[str] | None = None,
    all_files: set[str] | None = None,
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
        """Return the Python grammar."""
        return self._language

    def parse(self, source_bytes: bytes) -> tree_sitter.Tree:
        """Parse Python source bytes into a tree-sitter tree."""
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
        for _, match in cursor_dec.matches(tree.root_node):
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

        for _, match in cursor_sym.matches(tree.root_node):
            is_class = "class" in match
            node = match["class"][0] if is_class else match["func"][0]
            name_node = match["name"][0]
            name = _get_node_text(name_node)

            # Pop finished scopes
            while scope_stack and node.start_byte >= scope_stack[-1].end_byte:
                scope_stack.pop()

            # Immediate parent class for methods
            parent_class: str | None = None
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
        for _, match in cursor_imp.matches(tree.root_node):
            if "import" in match:
                node = match["import"][0]
                raw_text = _get_node_text(node).strip()
                line = node.start_point.row + 1

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
                line = node.start_point.row + 1

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

        def _clean_str(node: tree_sitter.Node) -> str | None:
            text = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()
            if len(text) >= 2 and text[0] in ("'", '"') and text[-1] == text[0]:
                return text[1:-1]
            return None

        def _get_node_text(node: tree_sitter.Node) -> str:
            return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

        for _, match in cursor.matches(tree.root_node):
            if "decorator" in match and "func_name" in match:
                dec_node = match["decorator"][0]
                func_node = match["func_name"][0]
                func_def_node = match.get("func", [func_node])[0]
                dec_text = source_bytes[dec_node.start_byte:dec_node.end_byte].decode("utf-8", errors="ignore").strip()
                func_name = source_bytes[func_node.start_byte:func_node.end_byte].decode("utf-8", errors="ignore").strip()
                dec_line = dec_node.start_point.row + 1
                handler_def_line = func_def_node.start_point.row + 1

                # Enclosing scope calculation
                module_name = path_to_module_name(path)
                ancestors: list[str] = []
                curr = func_def_node.parent
                while curr:
                    if curr.type in ("function_definition", "class_definition"):
                        for child in curr.children:
                            if child.type == "identifier":
                                ancestors.append(source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="ignore"))
                                break
                    curr = curr.parent
                ancestors.reverse()

                if ancestors:
                    enclosing_scope = ".".join([module_name] + ancestors) if module_name else ".".join(ancestors)
                else:
                    enclosing_scope = module_name or Path(path).stem

                handler_qname = f"{enclosing_scope}.{func_name}" if enclosing_scope else func_name

                route_info = parse_route_decorator(dec_text)
                if route_info:
                    # Generic dependency params -> middleware names (for uses edges).
                    dep_mw: list[str] = []
                    params_node = func_def_node.child_by_field_name("parameters")
                    if params_node:
                        for p in params_node.named_children:
                            txt = _get_node_text(p)
                            if "Depends(" in txt:
                                m = re.search(r"Depends\(\s*([A-Za-z_]\w*)", txt)
                                if m:
                                    dep_mw.append(m.group(1))
                    patterns.append(
                        {
                            "kind": "route",
                            "name": route_info["name"],
                            "middleware": dep_mw,
                            "url_path": route_info["url_path"],
                            "methods": route_info["methods"],
                            "handler": func_name,
                            "handler_qname": handler_qname,
                            "handler_line": handler_def_line,
                            "enclosing_scope": enclosing_scope,
                            "dec_line": dec_line,
                            "range": [
                                dec_node.start_point.row + 1,
                                dec_node.start_point.column,
                                dec_node.end_point.row + 1,
                                dec_node.end_point.column,
                            ],
                            "raw_text": dec_text,
                        }
                    )

                cmd_info = None
                if not route_info:  # dedupe: a route site cannot also be a command
                    cmd_info = parse_command_decorator(dec_text, func_name)
                if cmd_info:
                    patterns.append(
                        {
                            "kind": "command",
                            "name": cmd_info["command_name"],
                            "is_group": cmd_info["is_group"],
                            "handler": func_name,
                            "handler_qname": handler_qname,
                            "handler_line": handler_def_line,
                            "enclosing_scope": enclosing_scope,
                            "dec_line": dec_line,
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

        # Generic named registration -> command for call expressions.
        # Commands live in the CLI layer (structural path rule).
        is_cli_file = "cli/" in path.replace("\\", "/")
        claimed_lines = {p["range"][0] for p in patterns}
        channel_lines: set[int] = set()

        def _walk_named_calls(node: tree_sitter.Node):
            if is_cli_file and node.type == "call":
                line = node.start_point.row + 1
                if line not in claimed_lines and line not in channel_lines:
                    fn_node = node.child_by_field_name("function")
                    args_node = node.child_by_field_name("arguments")
                    if fn_node and args_node:
                        named_args = [
                            c for c in args_node.children
                            if c.type not in ("(", ")", ",")
                        ]
                        name = None
                        for a in named_args:
                            if a.type == "string":
                                name = _clean_str(a)
                                break
                        if name:
                            handler = None
                            for kw in named_args:
                                if kw.type == "keyword_argument":
                                    k = kw.child_by_field_name("name")
                                    v = kw.child_by_field_name("value")
                                    if k and _get_node_text(k).strip() in ("func", "handler", "callback") and v:
                                        handler = _get_node_text(v).strip().split(".")[0]
                                        break
                            if handler:
                                patterns.append({
                                    "kind": "command",
                                    "name": name,
                                    "handler": handler,
                                    "range": [line, node.start_point.column,
                                              node.end_point.row + 1, node.end_point.column],
                                    "raw_text": _get_node_text(node).strip(),
                                })
            for child in node.children:
                _walk_named_calls(child)

        _walk_named_calls(tree.root_node)

        # Fallback: a CLI-layer module with a top-level invocation but no
        # named registration is still a command (name = module name).
        if is_cli_file and not any(p["kind"] == "command" for p in patterns):
            module = Path(path).stem
            if module != "__init__":
                patterns.append({
                    "kind": "command",
                    "name": module,
                    "handler": module,
                    "range": [1, 0, 1, 0],
                    "raw_text": "module-level CLI invocation",
                })

        # Generic middleware detection (structural, no framework names):
        # - decorated function with 2+ params, one callable-like ("next"),
        #   registered with a string name -> middleware
        # - class with __call__ taking a "next"/app-like parameter -> middleware
        def _looks_like_middleware_params(params: list[str]) -> bool:
            if len(params) < 2:
                return False
            # One param is a callable passed through (next/call_next/app/send)
            callables = {"next", "call_next", "get_response", "app", "send", "receive"}
            return any(p in callables for p in params)

        for pos, node in enumerate(tree.root_node.children):
            if node.type == "decorated_definition":
                dec_texts = []
                fn_node = None
                for c in node.children:
                    if c.type == "decorator":
                        dec_texts.append(_get_node_text(c).strip().lstrip("@"))
                    elif c.type in ("function_definition", "async_function_definition"):
                        fn_node = c
                if fn_node and dec_texts:
                    name_node = fn_node.child_by_field_name("name")
                    params_node = fn_node.child_by_field_name("parameters")
                    params = []
                    if params_node:
                        for p in params_node.named_children:
                            pn = p.child_by_field_name("name") if hasattr(p, "child_by_field_name") else None
                            if pn:
                                params.append(_get_node_text(pn).strip())
                    has_string_name = any('("' in d or "('" in d for d in dec_texts)
                    if has_string_name and _looks_like_middleware_params(params) and name_node:
                        patterns.append({
                            "kind": "middleware",
                            "name": _get_node_text(name_node).strip(),
                            "range": [node.start_point.row + 1, node.start_point.column,
                                      node.end_point.row + 1, node.end_point.column],
                            "raw_text": _get_node_text(node).strip()[:200],
                        })
            elif node.type == "class_definition":
                cls_name_node = node.child_by_field_name("name")
                has_call = False
                call_params = []
                for c in node.named_children:
                    if c.type in ("function_definition", "async_function_definition"):
                        mname = c.child_by_field_name("name")
                        if mname and _get_node_text(mname).strip() == "__call__":
                            has_call = True
                            pn = c.child_by_field_name("parameters")
                            if pn:
                                for p in pn.named_children:
                                    nm = p.child_by_field_name("name") if hasattr(p, "child_by_field_name") else None
                                    if nm:
                                        call_params.append(_get_node_text(nm).strip())
                if has_call and cls_name_node and _looks_like_middleware_params(call_params):
                    patterns.append({
                        "kind": "middleware",
                        "name": _get_node_text(cls_name_node).strip(),
                        "range": [node.start_point.row + 1, node.start_point.column,
                                  node.end_point.row + 1, node.end_point.column],
                        "raw_text": _get_node_text(node).strip()[:200],
                    })

        # Sort patterns deterministically by line number
        patterns.sort(key=lambda p: (p["range"][0], p["name"]))
        return patterns

    def extract_channel_candidates(
        self, tree: tree_sitter.Tree, source_bytes: bytes, path: str
    ) -> list[dict[str, Any]]:
        """Extract message-broker channel candidates from Python source.

        Uses the same generic structural detector as the JS adapter:
        1. Binding: ``X("name", ...)`` where X is not a builtin -> binding (X -> "name")
        2. Member call: ``obj.method(...args)`` -> classified in merge.py via global binding map
        3. Direct call: ``fn("name", ...)`` with string first arg
        4. Decorator: ``@decorator(name="...")`` on a function -> processor candidate
        5. For-loop consumer: ``for x in binding:`` -> enclosing function is consumer
        6. Worker: ``X("name", fn)`` where X name contains "Worker"
        """
        candidates: list[dict[str, Any]] = []

        def _get_node_text(node: tree_sitter.Node) -> str:
            return source_bytes[node.start_byte : node.end_byte].decode(
                "utf-8", errors="replace"
            )

        def _clean_str(node: tree_sitter.Node) -> str | None:
            text = _get_node_text(node).strip()
            if (text.startswith('"') and text.endswith('"')) or (
                text.startswith("'") and text.endswith("'")
            ):
                return text[1:-1]
            if text.startswith('"""') and text.endswith('"""'):
                return text[3:-3]
            if text.startswith("'''") and text.endswith("'''"):
                return text[3:-3]
            return None

        def _kwarg_channel(call_node: tree_sitter.Node) -> str | None:
            """Extract channel name from common kwargs (routing_key, queue, topic, channel, name)."""
            for child in call_node.children:
                if child.type == "keyword_argument":
                    key_node = child.child_by_field_name("name")
                    val_node = child.child_by_field_name("value")
                    if key_node and val_node:
                        key = _get_node_text(key_node).strip()
                        if key in ("routing_key", "queue", "topic", "channel", "name"):
                            ch = _clean_str(val_node)
                            if ch is not None:
                                return ch
            return None

        def _enclosing_function(node: tree_sitter.Node) -> str | None:
            cur = node.parent
            while cur is not None:
                if cur.type == "function_definition":
                    name_node = cur.child_by_field_name("name")
                    if name_node:
                        return _get_node_text(name_node).strip()
                    return None
                cur = cur.parent
            return None

        # First pass: bindings, workers, decorators.
        def _walk_first_pass(node: tree_sitter.Node):
            # Binding or worker: X = X("name", ...) or X = X("name", fn)
            if node.type == "assignment":
                left = node.child_by_field_name("left")
                right = node.child_by_field_name("right")
                if left and right and right.type == "call":
                    var_name = _get_node_text(left).strip()
                    fn_node = right.child_by_field_name("function")
                    args_node = right.child_by_field_name("arguments")
                    if fn_node and args_node:
                        if fn_node.type == "identifier":
                            callee_name = _get_node_text(fn_node).strip()
                        elif fn_node.type == "attribute":
                            attr = fn_node.child_by_field_name("attribute")
                            callee_name = _get_node_text(attr).strip() if attr else ""
                        else:
                            callee_name = ""

                        named_args = [
                            c for c in args_node.children
                            if c.type not in ("(", ")", ",")
                        ]

                        # Check first positional string arg
                        first_str = None
                        if named_args and named_args[0].type == "string":
                            first_str = _clean_str(named_args[0])

                        # Also check kwargs for channel name
                        kw_ch = _kwarg_channel(right)

                        if first_str is not None or kw_ch is not None:
                            channel_name = first_str if first_str is not None else kw_ch
                            if channel_name is not None:
                                # Worker detection
                                if "worker" in callee_name.lower():
                                    processor_node = None
                                    processor_range = None
                                    if len(named_args) > 1:
                                        processor_node = named_args[1]
                                        processor_range = [
                                            processor_node.start_point.row + 1,
                                            processor_node.start_point.column,
                                            processor_node.end_point.row + 1,
                                            processor_node.end_point.column,
                                        ]
                                    candidates.append({
                                        "kind": "worker",
                                        "channel": channel_name,
                                        "file": path,
                                        "range": [
                                            right.start_point.row + 1,
                                            right.start_point.column,
                                            right.end_point.row + 1,
                                            right.end_point.column,
                                        ],
                                        "processor_range": processor_range,
                                        "processor_is_arrow": False,
                                    })
                                elif callee_name not in ("set", "dict", "list", "tuple", "str", "int", "float", "bool", "bytes", "print", "len", "range", "open", "sorted", "map", "filter", "zip", "enumerate"):
                                    candidates.append({
                                        "kind": "binding",
                                        "binding": var_name,
                                        "channel": channel_name,
                                        "file": path,
                                        "range": [
                                            right.start_point.row + 1,
                                            right.start_point.column,
                                            right.end_point.row + 1,
                                            right.end_point.column,
                                        ],
                                    })

            # Decorator detection: @decorator(name="...") on a function
            if node.type == "decorated_definition":
                for child in node.children:
                    if child.type == "decorator":
                        dec_text = _get_node_text(child).strip()
                        m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', dec_text)
                        if m:
                            channel_name = m.group(1)
                            for c in node.children:
                                if c.type == "function_definition":
                                    fn_name_node = c.child_by_field_name("name")
                                    if fn_name_node:
                                        candidates.append({
                                            "kind": "worker",
                                            "channel": channel_name,
                                            "file": path,
                                            "range": [
                                                c.start_point.row + 1,
                                                c.start_point.column,
                                                c.end_point.row + 1,
                                                c.end_point.column,
                                            ],
                                            "processor_range": [
                                                c.start_point.row + 1,
                                                c.start_point.column,
                                                c.end_point.row + 1,
                                                c.end_point.column,
                                            ],
                                            "processor_is_arrow": False,
                                        })

            for child in node.children:
                _walk_first_pass(child)

        _walk_first_pass(tree.root_node)

        # Second pass: member calls and direct calls.
        def _walk_second_pass(node: tree_sitter.Node):
            if node.type == "call":
                fn_node = node.child_by_field_name("function")
                args_node = node.child_by_field_name("arguments")
                if fn_node and args_node:
                    named_args = [
                        c for c in args_node.children
                        if c.type not in ("(", ")", ",")
                    ]

                    rng = [
                        node.start_point.row + 1,
                        node.start_point.column,
                        node.end_point.row + 1,
                        node.end_point.column,
                    ]

                    if fn_node.type == "attribute":
                        # member call: obj.method(...args)
                        obj_node = fn_node.child_by_field_name("object")
                        attr_node = fn_node.child_by_field_name("attribute")
                        if obj_node and attr_node:
                            candidates.append({
                                "kind": "member_call",
                                "object": _get_node_text(obj_node).strip(),
                                "method": _get_node_text(attr_node).strip(),
                                "has_payload": any(
                                    c.type not in ("lambda", "function_definition")
                                    for c in named_args
                                ),
                                "has_function": any(
                                    c.type in ("lambda", "function_definition")
                                    for c in named_args
                                ),
                                "first_str": _clean_str(named_args[0]) if named_args and named_args[0].type == "string" else None,
                                "function": _enclosing_function(node),
                                "file": path,
                                "range": rng,
                            })

                    elif fn_node.type == "identifier":
                        # direct call: fn("name", ...) or fn(..., name="...")
                        # Check first positional string
                        first_str = None
                        if named_args and named_args[0].type == "string":
                            first_str = _clean_str(named_args[0])
                        # Check kwargs
                        kw_ch = _kwarg_channel(node)
                        channel_name = first_str if first_str is not None else kw_ch
                        fn_name = _get_node_text(fn_node).strip()
                        if channel_name is not None and fn_name not in ("print", "len", "range", "open", "sorted", "map", "filter", "zip", "enumerate", "str", "int", "float", "bool", "list", "dict", "set", "tuple", "type", "isinstance", "hasattr", "getattr", "setattr", "input", "format", "repr", "abs", "min", "max", "sum", "any", "all", "next", "iter", "round", "pow", "divmod", "hex", "oct", "bin", "chr", "ord", "hash", "id", "vars", "dir", "help", "exit", "quit"):
                            has_payload = len(named_args) > 1 and any(
                                c.type not in ("lambda", "function_definition", "string")
                                for c in named_args[1:]
                            )
                            has_function = len(named_args) > 1 and any(
                                c.type in ("lambda", "function_definition")
                                for c in named_args[1:]
                            )
                            if not has_function and not has_payload and len(named_args) > 1:
                                has_payload = True
                            candidates.append({
                                "kind": "direct_call",
                                "function_name": fn_name,
                                "channel": channel_name,
                                "has_payload": has_payload,
                                "has_function": has_function,
                                "function": _enclosing_function(node),
                                "file": path,
                                "range": rng,
                            })

            # For-loop consumer detection: for x in binding: -> enclosing function is consumer
            if node.type == "for_statement":
                # for_statement: for X in Y: body
                # children: for, X, in, Y, :, body
                # The iterable is the node after 'in'
                iterable = None
                found_in = False
                for child in node.children:
                    if child.type == "in":
                        found_in = True
                        continue
                    if found_in and child.type not in (":",):
                        iterable = child
                        break
                if iterable and iterable.type == "identifier":
                    binding_name = _get_node_text(iterable).strip()
                    # Record as a member_call-like candidate so merge.py can
                    # resolve it via the global binding map. We use a special
                    # kind "for_loop_consumer" that merge.py handles.
                    candidates.append({
                        "kind": "for_loop_consumer",
                        "object": binding_name,
                        "has_payload": False,
                        "has_function": True,
                        "function": _enclosing_function(node),
                        "file": path,
                        "range": [
                            node.start_point.row + 1,
                            node.start_point.column,
                            node.end_point.row + 1,
                            node.end_point.column,
                        ],
                    })

            for child in node.children:
                _walk_second_pass(child)

        _walk_second_pass(tree.root_node)

        return candidates

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
            get_logger().warning(
                f"Import '{record.raw_text or record.specifier}' in '{from_file}' matches repo directory or file '{top_pkg}' but could not be resolved; treating as external."
            )

        return f"external:{top_pkg}"

