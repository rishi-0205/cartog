"""JavaScript and TypeScript Language Adapter using tree-sitter."""

import os
import re
from pathlib import Path
from typing import Any, NamedTuple

import tree_sitter
import tree_sitter_javascript
import tree_sitter_typescript

from cartog.core.jsonc import load_jsonc_file, load_strict_json_file
from cartog.parse.base import (
    ImportRecord,
    LanguageAdapter,
    ProjectContext,
    SymbolRecord,
)

CANDIDATE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json")
CANDIDATE_INDEX_FILES = (
    "index.ts",
    "index.tsx",
    "index.js",
    "index.jsx",
    "index.mjs",
    "index.cjs",
    "index.json",
)


class ScopeEntry(NamedTuple):
    """One lexical scope pushed while scanning JavaScript/TypeScript source."""
    name: str
    end_byte: int
    is_class: bool


def clean_string_literal(text: str) -> str:
    """Strip quotes from JS/TS string literals."""
    text = text.strip()
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        return text[1:-1]
    if text.startswith("`") and text.endswith("`"):
        return text[1:-1]
    return text


def get_enclosing_root(rel_path: str, roots: list[str]) -> str:
    """Return the longest matching root prefix for a path, or '.' if none."""
    p_str = rel_path.replace("\\", "/")
    best_root = "."
    best_len = 0
    for r in roots:
        if r == ".":
            continue
        r_clean = r.replace("\\", "/").rstrip("/")
        if p_str == r_clean or p_str.startswith(r_clean + "/"):
            if len(r_clean) > best_len:
                best_root = r_clean
                best_len = len(r_clean)
    return best_root


def path_to_js_module_name(rel_path: str, roots: list[str] | None = None) -> str:
    """Convert a repo-relative path into a JS/TS module name relative to its enclosing root and source folder."""
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
    for ext in (".tsx", ".ts", ".jsx", ".js", ".mjs", ".cjs"):
        if last.endswith(ext):
            last = last[: -len(ext)]
            break

    if last == "index":
        parts = parts[:-1]
    else:
        parts[-1] = last
    return ".".join(parts)


def extract_nextjs_route_path(file_path: str) -> tuple[str | None, str | None]:
    """Derive Next.js route URL and router kind ('app' or 'pages') from file path."""
    p_str = file_path.replace("\\", "/")
    parts = p_str.split("/")

    # App Router: app/**/route.(ts|js|tsx|jsx)
    if "app" in parts and parts[-1].startswith("route."):
        app_idx = parts.index("app")
        route_parts = parts[app_idx + 1 : -1]
        # Filter out route groups like (marketing), (auth)
        filtered = [pt for pt in route_parts if not (pt.startswith("(") and pt.endswith(")"))]
        url = "/" + "/".join(filtered) if filtered else "/"
        return ("app", url)

    # Pages Router: pages/api/**
    if "pages" in parts and "api" in parts:
        pages_idx = parts.index("pages")
        if pages_idx + 1 < len(parts) and parts[pages_idx + 1] == "api":
            sub_parts = parts[pages_idx + 1 :]
            last = sub_parts[-1]
            last = re.sub(r"\.(ts|js|tsx|jsx)$", "", last)
            if last == "index":
                sub_parts = sub_parts[:-1]
            else:
                sub_parts[-1] = last
            url = "/" + "/".join(sub_parts)
            return ("pages", url)

    return (None, None)


class JsAdapter(LanguageAdapter):
    """Tree-sitter adapter for JavaScript, TypeScript, and TSX source code."""

    name = "javascript"
    extensions = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")
    version = "1.0.0"

    def __init__(self):
        self._lang_js = tree_sitter.Language(tree_sitter_javascript.language())
        self._lang_ts = tree_sitter.Language(tree_sitter_typescript.language_typescript())
        self._lang_tsx = tree_sitter.Language(tree_sitter_typescript.language_tsx())
        self._parser_js = tree_sitter.Parser(self._lang_js)
        self._parser_ts = tree_sitter.Parser(self._lang_ts)
        self._parser_tsx = tree_sitter.Parser(self._lang_tsx)

        # Caches for project configurations
        self._tsconfig_cache: dict[str, dict[str, Any] | None] = {}
        self._workspaces_cache: dict[str, dict[str, str]] | None = None

    def grammar_for(self, path: Path) -> tree_sitter.Language:
        """Return the JavaScript, TypeScript or TSX grammar matching the file suffix."""
        suffix = path.suffix.lower()
        if suffix == ".tsx":
            return self._lang_tsx
        elif suffix == ".ts":
            return self._lang_ts
        return self._lang_js

    def parse(
        self, source_bytes: bytes, path: Path | str | None = None
    ) -> tree_sitter.Tree:
        """Parse source bytes with the grammar implied by ``path`` (default JavaScript)."""
        if path is not None:
            suffix = Path(path).suffix.lower()
            if suffix == ".tsx":
                return self._parser_tsx.parse(source_bytes)
            elif suffix == ".ts":
                return self._parser_ts.parse(source_bytes)
        return self._parser_js.parse(source_bytes)

    def extract_symbols(
        self, tree: tree_sitter.Tree, source_bytes: bytes, path: str
    ) -> list[SymbolRecord]:
        """Extract functions, methods, classes, and arrow functions with qualified names."""
        module_name = path_to_js_module_name(path)
        symbols: list[SymbolRecord] = []

        def _get_node_text(node: tree_sitter.Node) -> str:
            return source_bytes[node.start_byte : node.end_byte].decode(
                "utf-8", errors="replace"
            )

        def _extract_decorators(node: tree_sitter.Node) -> list[str]:
            decs = []
            for child in node.children:
                if child.type == "decorator":
                    d_text = _get_node_text(child).strip()
                    if d_text.startswith("@"):
                        d_text = d_text[1:].strip()
                    decs.append(d_text)
            return decs

        scope_stack: list[ScopeEntry] = []

        def _walk(node: tree_sitter.Node):
            # Pop finished scopes
            while scope_stack and node.start_byte >= scope_stack[-1].end_byte:
                scope_stack.pop()

            is_class = node.type == "class_declaration"
            is_func = node.type in (
                "function_declaration",
                "generator_function_declaration",
            )
            is_method = node.type == "method_definition"
            is_var_func = False
            var_name: str | None = None

            if node.type == "variable_declarator":
                val = node.child_by_field_name("value")
                if val and val.type in (
                    "arrow_function",
                    "function_expression",
                    "generator_function_declaration",
                ):
                    name_node = node.child_by_field_name("name")
                    if name_node and name_node.type == "identifier":
                        is_var_func = True
                        var_name = _get_node_text(name_node)

            if is_class or is_func or is_method or is_var_func:
                name_node = node.child_by_field_name("name")
                name = var_name or (
                    _get_node_text(name_node) if name_node else "default"
                )

                # Determine immediate parent class
                parent_class: str | None = None
                if scope_stack and scope_stack[-1].is_class:
                    parent_class = scope_stack[-1].name

                if is_class:
                    kind = "class"
                elif parent_class is not None or is_method:
                    kind = "method"
                else:
                    kind = "function"

                # Build qualified name
                qname_parts = [module_name] if module_name else []
                for entry in scope_stack:
                    qname_parts.append(entry.name)
                qname_parts.append(name)
                qname = ".".join(qname_parts)

                # Check async
                is_async = False
                if not is_class:
                    val_node = node.child_by_field_name("value") if is_var_func else node
                    if val_node:
                        prefix = source_bytes[
                            val_node.start_byte : min(
                                val_node.start_byte + 10, len(source_bytes)
                            )
                        ]
                        is_async = b"async" in prefix

                decorators = _extract_decorators(node)
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
                scope_stack.append(
                    ScopeEntry(name=name, end_byte=node.end_byte, is_class=is_class)
                )

            for child in node.children:
                _walk(child)

        _walk(tree.root_node)

        # Sort symbols deterministically by start line, start col, and name
        symbols.sort(key=lambda s: (s.start_line, s.start_col, s.name))
        return symbols

    def extract_imports(
        self, tree: tree_sitter.Tree, source_bytes: bytes, path: str
    ) -> list[ImportRecord]:
        """Extract ESM imports, re-exports, CommonJS require(), and dynamic import()."""
        imports: list[ImportRecord] = []

        def _get_node_text(node: tree_sitter.Node) -> str:
            return source_bytes[node.start_byte : node.end_byte].decode(
                "utf-8", errors="replace"
            )

        def _count_level(spec: str) -> int:
            if not spec.startswith("."):
                return 0
            dots = 0
            parts = spec.split("/")
            for p in parts:
                if p == "..":
                    dots += 1
                elif p == ".":
                    if dots == 0:
                        dots = 1
                else:
                    break
            return dots if dots > 0 else 1

        def _process_import_node(node: tree_sitter.Node):
            # 1. ESM import statement
            if node.type == "import_statement":
                raw_text = _get_node_text(node).strip()
                source_node = None
                for c in node.children:
                    if c.type == "string":
                        source_node = c
                        break
                if not source_node:
                    return

                specifier = clean_string_literal(_get_node_text(source_node))
                names: list[str] = []
                aliases: dict[str, str] = {}
                is_type_only = False

                for c in node.children:
                    if _get_node_text(c).strip() == "type":
                        is_type_only = True
                    elif c.type == "import_clause":
                        for gc in c.children:
                            if _get_node_text(gc).strip() == "type":
                                is_type_only = True
                            elif gc.type == "identifier":
                                default_name = _get_node_text(gc).strip()
                                names.append("default")
                                aliases["default"] = default_name
                            elif gc.type == "namespace_import":
                                for sc in gc.children:
                                    if sc.type == "identifier":
                                        ns_name = _get_node_text(sc).strip()
                                        names.append("*")
                                        aliases["*"] = ns_name
                            elif gc.type == "named_imports":
                                for sc in gc.children:
                                    if sc.type == "import_specifier":
                                        n_c = sc.child_by_field_name("name")
                                        a_c = sc.child_by_field_name("alias")
                                        if n_c:
                                            n = _get_node_text(n_c).strip()
                                            names.append(n)
                                            if a_c:
                                                aliases[n] = _get_node_text(a_c).strip()

                is_rel = specifier.startswith(".")
                kind = "relative" if is_rel else "from"
                imports.append(
                    ImportRecord(
                        specifier=specifier,
                        names=names,
                        aliases=aliases,
                        kind=kind,
                        line=node.start_point.row + 1,
                        level=_count_level(specifier),
                        raw_text=raw_text,
                        is_type_only=is_type_only,
                    )
                )

            # 2. ESM export ... from statement (re-export dependency)
            elif node.type == "export_statement":
                raw_text = _get_node_text(node).strip()
                source_node = None
                for c in node.children:
                    if c.type == "string":
                        source_node = c
                        break
                if source_node:
                    specifier = clean_string_literal(_get_node_text(source_node))
                    names: list[str] = []
                    aliases: dict[str, str] = {}
                    is_type_only = False

                    for c in node.children:
                        if _get_node_text(c).strip() == "type":
                            is_type_only = True
                        elif c.type == "export_clause":
                            for sc in c.children:
                                if _get_node_text(sc).strip() == "type":
                                    is_type_only = True
                                elif sc.type == "export_specifier":
                                    n_c = sc.child_by_field_name("name")
                                    a_c = sc.child_by_field_name("alias")
                                    if n_c:
                                        n = _get_node_text(n_c).strip()
                                        names.append(n)
                                        if a_c:
                                            aliases[n] = _get_node_text(a_c).strip()
                        elif _get_node_text(c).strip() == "*":
                            names.append("*")

                    is_rel = specifier.startswith(".")
                    kind = "relative" if is_rel else "from"
                    imports.append(
                        ImportRecord(
                            specifier=specifier,
                            names=names,
                            aliases=aliases,
                            kind=kind,
                            line=node.start_point.row + 1,
                            level=_count_level(specifier),
                            raw_text=raw_text,
                            is_type_only=is_type_only,
                        )
                    )

            # 3. Call expressions: require() or dynamic import()
            elif node.type == "call_expression":
                fn_node = node.child_by_field_name("function")
                args_node = node.child_by_field_name("arguments")
                if fn_node and args_node:
                    fn_text = _get_node_text(fn_node).strip()
                    if fn_text == "require" or fn_text == "import" or fn_node.type == "import":
                        string_args = [c for c in args_node.children if c.type == "string"]
                        if string_args:
                            specifier = clean_string_literal(_get_node_text(string_args[0]))
                            is_rel = specifier.startswith(".")
                            kind = "relative" if is_rel else "standard"
                            imports.append(
                                ImportRecord(
                                    specifier=specifier,
                                    names=[],
                                    aliases={},
                                    kind=kind,
                                    line=node.start_point.row + 1,
                                    level=_count_level(specifier),
                                    raw_text=_get_node_text(node).strip(),
                                )
                            )

            for child in node.children:
                _process_import_node(child)

        _process_import_node(tree.root_node)

        # Sort imports deterministically by line number and specifier
        imports.sort(key=lambda i: (i.line, i.specifier))
        return imports

    def _get_tsconfig(
        self, root_dir: str, target_path: str = ".", project_context: ProjectContext | None = None
    ) -> dict[str, Any] | None:
        """Load and cache tsconfig.json or jsconfig.json for a given directory."""
        cache_key = f"{target_path}::{root_dir}"
        if cache_key in self._tsconfig_cache:
            return self._tsconfig_cache[cache_key]

        target_p = Path(target_path) if target_path != "." else Path("")
        base_p = (target_p / root_dir) if root_dir != "." else target_p
        ts_p = base_p / "tsconfig.json"
        js_p = base_p / "jsconfig.json"

        data = None
        ctx = project_context or getattr(self, "context", None)
        if ts_p.is_file():
            data = load_jsonc_file(ts_p, ctx)
        elif js_p.is_file():
            data = load_jsonc_file(js_p, ctx)

        self._tsconfig_cache[cache_key] = data
        return data

    def _discover_workspace_packages(
        self, project_context: ProjectContext
    ) -> dict[str, dict[str, Any]]:
        """Discover packages in root package.json and monorepo workspaces."""
        target_path = getattr(project_context, "target_path", ".") or "."
        if self._workspaces_cache is not None and target_path in self._workspaces_cache:
            return self._workspaces_cache[target_path]

        packages: dict[str, dict[str, Any]] = {}
        roots = getattr(project_context, "roots", ["."]) or ["."]
        target_p = Path(target_path) if target_path != "." else Path("")

        for r in roots:
            base_p = (target_p / r) if r != "." else target_p
            pkg_json = base_p / "package.json"
            if not pkg_json.is_file():
                continue

            data = load_strict_json_file(pkg_json, project_context)
            if not data or not isinstance(data, dict):
                continue

            try:
                rel_pkg_dir = base_p.relative_to(target_p).as_posix() if target_p != Path("") else (r if r != "." else ".")
            except ValueError:
                rel_pkg_dir = r if r != "." else "."
            if rel_pkg_dir == "":
                rel_pkg_dir = "."

            # 1. Register package itself if it defines a name
            if "name" in data and isinstance(data["name"], str):
                packages[data["name"]] = {
                    "dir": rel_pkg_dir,
                    "data": data,
                    "main": data.get("main"),
                    "module": data.get("module"),
                    "types": data.get("types"),
                    "exports": data.get("exports"),
                }

            # 2. Register child workspace packages if declared
            workspaces = data.get("workspaces", [])
            if isinstance(workspaces, dict):
                workspaces = workspaces.get("packages", [])
            if not isinstance(workspaces, list):
                continue

            for pattern in workspaces:
                clean_pat = pattern.rstrip("/")
                if clean_pat.endswith("/*"):
                    parent_dir = base_p / clean_pat[:-2]
                    if parent_dir.is_dir():
                        try:
                            for child in parent_dir.iterdir():
                                if child.is_dir():
                                    child_pkg = child / "package.json"
                                    if child_pkg.is_file():
                                        c_data = load_strict_json_file(child_pkg, project_context)
                                        if c_data and "name" in c_data and isinstance(c_data["name"], str):
                                            try:
                                                c_rel = child.relative_to(target_p).as_posix() if target_p != Path("") else child.as_posix()
                                            except ValueError:
                                                c_rel = child.as_posix()
                                            packages[c_data["name"]] = {
                                                "dir": c_rel,
                                                "data": c_data,
                                                "main": c_data.get("main"),
                                                "module": c_data.get("module"),
                                                "types": c_data.get("types"),
                                                "exports": c_data.get("exports"),
                                            }
                        except Exception:
                            pass
                else:
                    target_dir = base_p / clean_pat
                    child_pkg = target_dir / "package.json"
                    if child_pkg.is_file():
                        c_data = load_strict_json_file(child_pkg, project_context)
                        if c_data and "name" in c_data and isinstance(c_data["name"], str):
                            try:
                                c_rel = target_dir.relative_to(target_p).as_posix() if target_p != Path("") else target_dir.as_posix()
                            except ValueError:
                                c_rel = target_dir.as_posix()
                            packages[c_data["name"]] = {
                                "dir": c_rel,
                                "data": c_data,
                                "main": c_data.get("main"),
                                "module": c_data.get("module"),
                                "types": c_data.get("types"),
                                "exports": c_data.get("exports"),
                            }

        if self._workspaces_cache is None:
            self._workspaces_cache = {}
        self._workspaces_cache[target_path] = packages
        return packages

    def _get_tsconfig_build_dirs(
        self, pkg_dir: str, target_path: str = ".", project_context: ProjectContext | None = None
    ) -> list[tuple[str, str]]:
        """Return list of (outDir, rootDir) mappings from tsconfig files in pkg_dir."""
        target_p = Path(target_path) if target_path != "." else Path("")
        base_p = (target_p / pkg_dir) if pkg_dir != "." else target_p
        mappings: list[tuple[str, str]] = []
        ctx = project_context or getattr(self, "context", None)

        for fn in ("tsconfig.dist.json", "tsconfig.build.json", "tsconfig.json"):
            cfg_p = base_p / fn
            if cfg_p.is_file():
                data = load_jsonc_file(cfg_p, ctx)
                if data and isinstance(data, dict):
                    copts = data.get("compilerOptions", {})
                    if isinstance(copts, dict) and "outDir" in copts:
                        out_d = copts["outDir"].strip()
                        root_d = copts.get("rootDir", ".").strip()
                        out_norm = os.path.normpath(out_d).replace("\\", "/").lstrip("./")
                        root_norm = os.path.normpath(root_d).replace("\\", "/").lstrip("./")
                        if out_norm and (out_norm, root_norm) not in mappings:
                            mappings.append((out_norm, root_norm))
        return mappings

    def _resolve_package_entry(
        self,
        pkg_name: str,
        subpath: str | None,
        pkg_info: dict[str, Any],
        all_files: set[str],
        target_path: str = ".",
        project_context: ProjectContext | None = None,
    ) -> str | None:
        """Resolve a self-referencing package entrypoint or subpath to a repo source file."""
        pkg_dir = pkg_info.get("dir", ".")
        pkg_data = pkg_info.get("data", {})
        exports = pkg_info.get("exports") or pkg_data.get("exports")

        candidates: list[str] = []

        if subpath is None:
            # 1. Check exports for root entry "."
            if exports:
                if isinstance(exports, str):
                    candidates.append(exports)
                elif isinstance(exports, dict):
                    entry = exports.get(".")
                    if isinstance(entry, str):
                        candidates.append(entry)
                    elif isinstance(entry, dict):
                        for cond in ("types", "import", "module", "default"):
                            if cond in entry and isinstance(entry[cond], str):
                                candidates.append(entry[cond])
                        for v in entry.values():
                            if isinstance(v, str) and v not in candidates:
                                candidates.append(v)
                    elif "." not in exports:
                        for cond in ("types", "import", "module", "default"):
                            if cond in exports and isinstance(exports[cond], str):
                                candidates.append(exports[cond])
                        for v in exports.values():
                            if isinstance(v, str) and v not in candidates:
                                candidates.append(v)
            # 2. Check module, main, types in package.json
            for k in ("module", "main", "types"):
                v = pkg_info.get(k) or pkg_data.get(k)
                if v and isinstance(v, str) and v not in candidates:
                    candidates.append(v)
        else:
            # Subpath import (e.g. ky/foo)
            exp_key = f"./{subpath}"
            if exports and isinstance(exports, dict):
                if exp_key in exports:
                    v = exports[exp_key]
                    if isinstance(v, str):
                        candidates.append(v)
                    elif isinstance(v, dict):
                        for cond in ("types", "import", "module", "default"):
                            if cond in v and isinstance(v[cond], str):
                                candidates.append(v[cond])
                        for val in v.values():
                            if isinstance(val, str) and val not in candidates:
                                candidates.append(val)
                else:
                    for pat, val in exports.items():
                        if pat.startswith("./") and "*" in pat:
                            prefix, suffix = pat.split("*", 1)
                            if exp_key.startswith(prefix) and (not suffix or exp_key.endswith(suffix)):
                                wildcard = exp_key[len(prefix) : len(exp_key) - len(suffix) if suffix else None]
                                if isinstance(val, str):
                                    candidates.append(val.replace("*", wildcard))
                                elif isinstance(val, dict):
                                    for cond in ("types", "import", "module", "default"):
                                        if cond in val and isinstance(val[cond], str):
                                            candidates.append(val[cond].replace("*", wildcard))
                                    for v_item in val.values():
                                        if isinstance(v_item, str):
                                            repl = v_item.replace("*", wildcard)
                                            if repl not in candidates:
                                                candidates.append(repl)
            candidates.append(subpath)
            candidates.append(f"./{subpath}")

        def _make_repo_path(path_str: str) -> Path:
            clean = path_str.strip()
            if clean.startswith("./"):
                clean = clean[2:]
            if pkg_dir != ".":
                return Path(pkg_dir) / clean
            return Path(clean)

        # Step 1: Probe direct candidates
        for cand in candidates:
            target_p = _make_repo_path(cand)
            res = self._probe_candidate(target_p, all_files)
            if res:
                return res

        # Step 2: Built output mapping using tsconfig outDir and rootDir
        build_dirs = self._get_tsconfig_build_dirs(
            pkg_dir, target_path=target_path, project_context=project_context
        )
        for cand in candidates:
            clean_cand = cand.strip()
            if clean_cand.startswith("./"):
                clean_cand = clean_cand[2:]

            for out_dir, root_dir in build_dirs:
                if clean_cand.startswith(out_dir + "/") or clean_cand == out_dir:
                    sub_in_out = clean_cand[len(out_dir) :].lstrip("/")
                    src_cand = f"{root_dir}/{sub_in_out}" if root_dir else sub_in_out
                    target_p = _make_repo_path(src_cand)
                    res = self._probe_candidate(target_p, all_files)
                    if res:
                        return res
                    if sub_in_out.endswith(".d.ts"):
                        base_no_ext = sub_in_out[:-5]
                        target_p2 = _make_repo_path(f"{root_dir}/{base_no_ext}.ts" if root_dir else f"{base_no_ext}.ts")
                        res2 = self._probe_candidate(target_p2, all_files)
                        if res2:
                            return res2

        # Step 3: Fallback source directories (source, src, lib)
        for cand in candidates:
            clean_cand = cand.strip()
            if clean_cand.startswith("./"):
                clean_cand = clean_cand[2:]
            parts = clean_cand.split("/", 1)
            rest = parts[1] if len(parts) > 1 else parts[0]
            for src_folder in ("source", "src", "lib"):
                target_p = _make_repo_path(f"{src_folder}/{rest}")
                res = self._probe_candidate(target_p, all_files)
                if res:
                    return res

        # Step 4: Fallback standard entry points for root package
        if subpath is None:
            for fb in ("source/index.ts", "src/index.ts", "index.ts", "source/index.js", "src/index.js", "index.js"):
                target_p = _make_repo_path(fb)
                res = self._probe_candidate(target_p, all_files)
                if res:
                    return res

        return None

    def _resolve_relative(
        self, specifier: str, from_file: str, all_files: set[str]
    ) -> str | None:
        """Resolve a relative import specifier with JS/TS extension rewriting and index probing."""
        from_dir = Path(from_file).parent
        # Remove leading ./ for clean joining
        clean_spec = specifier
        target_base = (from_dir / clean_spec)

        # Probing helper
        def _probe(base_path: Path) -> str | None:
            # Normalize path relative to repo root
            # Normalize away .. and .
            try:
                norm_str = os.path.normpath(base_path.as_posix()).replace("\\", "/")
            except Exception:
                norm_str = base_path.as_posix()
            if norm_str.startswith("./"):
                norm_str = norm_str[2:]

            # Direct match
            if norm_str in all_files:
                return norm_str

            # Check .js -> .ts / .tsx replacement rule
            for js_ext, ts_replacements in [
                (".js", [".ts", ".tsx", ".js", ".mjs"]),
                (".jsx", [".tsx", ".jsx"]),
                (".mjs", [".mts", ".mjs"]),
                (".cjs", [".cts", ".cjs"]),
            ]:
                if norm_str.endswith(js_ext):
                    prefix = norm_str[: -len(js_ext)]
                    for repl in ts_replacements:
                        cand = prefix + repl
                        if cand in all_files:
                            return cand

            # If no extension was specified, probe extensions
            for ext in CANDIDATE_EXTENSIONS:
                cand = norm_str + ext
                if cand in all_files:
                    return cand

            # Probe index files inside directory
            for idx in CANDIDATE_INDEX_FILES:
                cand = f"{norm_str}/{idx}"
                if cand in all_files:
                    return cand

            return None

        return _probe(target_base)

    def resolve_import(
        self, record: ImportRecord, from_file: str, project_context: ProjectContext
    ) -> str:
        """Resolve a JS/TS ImportRecord to an internal repo path, external package, or unresolved."""
        specifier = record.specifier.strip()
        if not specifier:
            return "unresolved"

        all_files = getattr(project_context, "all_files", set())
        roots = getattr(project_context, "roots", ["."]) or ["."]

        # 1. Relative import resolution (starts with . or ..)
        if specifier.startswith("."):
            res = self._resolve_relative(specifier, from_file, all_files)
            if res:
                return res
            return "unresolved"

        # 2. tsconfig.json / jsconfig.json paths alias mapping
        target_path = getattr(project_context, "target_path", ".") or "."
        enc_root = get_enclosing_root(from_file, roots)
        search_roots = [enc_root] + [r for r in roots if r != enc_root]
        for r in search_roots:
            cfg = self._get_tsconfig(r, target_path=target_path, project_context=project_context)
            if not cfg or not isinstance(cfg, dict):
                continue
            compiler_opts = cfg.get("compilerOptions", {})
            if not isinstance(compiler_opts, dict):
                continue

            base_url = compiler_opts.get("baseUrl", ".")
            paths_map = compiler_opts.get("paths", {})
            if not isinstance(paths_map, dict):
                continue

            root_p = Path(r) if r != "." else Path("")
            base_url_p = root_p / base_url

            for pattern, targets in paths_map.items():
                if not isinstance(targets, list):
                    continue
                # e.g. "@core/*" -> ["packages/core/src/*"]
                if "*" in pattern:
                    prefix, suffix = pattern.split("*", 1)
                    if specifier.startswith(prefix) and (
                        not suffix or specifier.endswith(suffix)
                    ):
                        wildcard = specifier[len(prefix) : len(specifier) - len(suffix) if suffix else None]
                        for target_tmpl in targets:
                            replaced = target_tmpl.replace("*", wildcard)
                            cand_base = base_url_p / replaced
                            cand_res = self._probe_candidate(cand_base, all_files)
                            if cand_res:
                                return cand_res
                elif specifier == pattern:
                    for target_tmpl in targets:
                        cand_base = base_url_p / target_tmpl
                        cand_res = self._probe_candidate(cand_base, all_files)
                        if cand_res:
                            return cand_res

        # 3. Monorepo workspace package and root package resolution
        ws_pkgs = self._discover_workspace_packages(project_context)
        for pkg_name, pkg_info in sorted(ws_pkgs.items(), key=lambda x: len(x[0]), reverse=True):
            if specifier == pkg_name:
                res = self._resolve_package_entry(
                    pkg_name,
                    None,
                    pkg_info,
                    all_files,
                    target_path=target_path,
                    project_context=project_context,
                )
                if res:
                    return res
            elif specifier.startswith(pkg_name + "/"):
                sub_path = specifier[len(pkg_name) + 1 :]
                res = self._resolve_package_entry(
                    pkg_name,
                    sub_path,
                    pkg_info,
                    all_files,
                    target_path=target_path,
                    project_context=project_context,
                )
                if res:
                    return res

        # 4. External package resolution
        # Handle scoped packages (e.g. @sindresorhus/is -> @sindresorhus/is)
        if specifier.startswith("@"):
            parts = specifier.split("/")
            top_pkg = "/".join(parts[:2]) if len(parts) >= 2 else parts[0]
        else:
            top_pkg = specifier.split("/")[0]

        return f"external:{top_pkg}"

    def _probe_candidate(self, cand_base: Path, all_files: set[str]) -> str | None:
        """Probe a candidate file path with standard extensions and directory indexes."""
        try:
            norm = os.path.normpath(cand_base.as_posix()).replace("\\", "/")
        except Exception:
            norm = cand_base.as_posix()
        if norm.startswith("./"):
            norm = norm[2:]

        if norm in all_files:
            return norm

        # If .d.ts, probe .ts, .tsx, .d.ts
        if norm.endswith(".d.ts"):
            prefix = norm[:-5]
            for ext in (".ts", ".tsx", ".d.ts"):
                cand = prefix + ext
                if cand in all_files:
                    return cand

        # Check .js -> .ts / .tsx replacement rule
        for js_ext, ts_replacements in [
            (".js", [".ts", ".tsx", ".js", ".mjs"]),
            (".jsx", [".tsx", ".jsx"]),
            (".mjs", [".mts", ".mjs"]),
            (".cjs", [".cts", ".cjs"]),
        ]:
            if norm.endswith(js_ext):
                prefix = norm[: -len(js_ext)]
                for repl in ts_replacements:
                    cand = prefix + repl
                    if cand in all_files:
                        return cand

        # Probing extensions
        for ext in CANDIDATE_EXTENSIONS:
            cand = norm + ext
            if cand in all_files:
                return cand

        # Probing index files
        for idx in CANDIDATE_INDEX_FILES:
            cand = f"{norm}/{idx}"
            if cand in all_files:
                return cand

        return None

    def extract_channel_candidates(
        self, tree: tree_sitter.Tree, source_bytes: bytes, path: str
    ) -> list[dict[str, Any]]:
        """Extract message-broker channel candidates from JS/TS source.

        Returns raw candidates that are classified and paired in merge.py:
        - ``binding``: a variable bound to a channel name via
          ``new X("name", ...)`` (X not a builtin).
        - ``member_call``: a call ``obj.method(...args)`` where obj is a
          potential channel binding (resolved cross-file in merge.py).
        - ``direct_call``: a call ``fn("name", ...)`` with a string first arg.
        - ``worker``: ``new Worker("name", fn)``.
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
            if text.startswith("`") and text.endswith("`"):
                return text[1:-1]
            return None

        def _enclosing_function(node: tree_sitter.Node) -> str | None:
            cur = node.parent
            while cur is not None:
                if cur.type in (
                    "function_declaration",
                    "generator_function_declaration",
                    "method_definition",
                    "arrow_function",
                    "function_expression",
                ):
                    name_node = cur.child_by_field_name("name")
                    if name_node:
                        return _get_node_text(name_node).strip()
                    if cur.type == "arrow_function" and cur.parent and cur.parent.type == "variable_declarator":
                        vn = cur.parent.child_by_field_name("name")
                        if vn and vn.type == "identifier":
                            return _get_node_text(vn).strip()
                    return None
                cur = cur.parent
            return None

        # First pass: bindings and workers.
        def _walk_first_pass(node: tree_sitter.Node):
            if node.type == "variable_declarator":
                name_node = node.child_by_field_name("name")
                value_node = node.child_by_field_name("value")
                if name_node and value_node and value_node.type == "new_expression":
                    var_name = _get_node_text(name_node).strip()
                    callee = value_node.child_by_field_name("constructor")
                    args = value_node.child_by_field_name("arguments")
                    if callee and args:
                        callee_text = _get_node_text(callee).strip()
                        named_args = [
                            c for c in args.children
                            if c.type not in ("(", ")", ",")
                        ]
                        if named_args and named_args[0].type == "string":
                            channel_name = _clean_str(named_args[0])
                            if channel_name is not None:
                                ctor_name = callee_text.split(".")[-1] if "." in callee_text else callee_text
                                if ctor_name == "Worker":
                                    processor_node = named_args[1] if len(named_args) > 1 else None
                                    processor_range = None
                                    if processor_node:
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
                                            value_node.start_point.row + 1,
                                            value_node.start_point.column,
                                            value_node.end_point.row + 1,
                                            value_node.end_point.column,
                                        ],
                                        "processor_range": processor_range,
                                        "processor_is_arrow": processor_node is not None and processor_node.type == "arrow_function",
                                    })
                                elif ctor_name not in ("Set", "Map", "Array", "Object", "Date", "RegExp", "Error", "Promise"):
                                    candidates.append({
                                        "kind": "binding",
                                        "binding": var_name,
                                        "channel": channel_name,
                                        "file": path,
                                        "range": [
                                            value_node.start_point.row + 1,
                                            value_node.start_point.column,
                                            value_node.end_point.row + 1,
                                            value_node.end_point.column,
                                        ],
                                    })

            for child in node.children:
                _walk_first_pass(child)

        _walk_first_pass(tree.root_node)

        # Second pass: member calls and direct calls.
        def _walk_second_pass(node: tree_sitter.Node):
            if node.type == "call_expression":
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

                    if fn_node.type == "member_expression":
                        obj_node = fn_node.child_by_field_name("object")
                        prop_node = fn_node.child_by_field_name("property")
                        if obj_node and prop_node:
                            candidates.append({
                                "kind": "member_call",
                                "object": _get_node_text(obj_node).strip(),
                                "method": _get_node_text(prop_node).strip(),
                                "has_payload": any(
                                    c.type not in ("arrow_function", "function_expression", "function")
                                    for c in named_args
                                ),
                                "has_function": any(
                                    c.type in ("arrow_function", "function_expression", "function")
                                    for c in named_args
                                ),
                                "function": _enclosing_function(node),
                                "file": path,
                                "range": rng,
                            })

                    elif fn_node.type == "identifier":
                        if named_args and named_args[0].type == "string":
                            channel_name = _clean_str(named_args[0])
                            if channel_name is not None:
                                has_payload = len(named_args) > 1 and any(
                                    c.type not in ("arrow_function", "function_expression", "function")
                                    for c in named_args[1:]
                                )
                                has_function = len(named_args) > 1 and any(
                                    c.type in ("arrow_function", "function_expression", "function")
                                    for c in named_args[1:]
                                )
                                candidates.append({
                                    "kind": "direct_call",
                                    "function_name": _get_node_text(fn_node).strip().lower(),
                                    "channel": channel_name,
                                    "has_payload": has_payload,
                                    "has_function": has_function,
                                    "function": _enclosing_function(node),
                                    "file": path,
                                    "range": rng,
                                })

            for child in node.children:
                _walk_second_pass(child)

        _walk_second_pass(tree.root_node)

        return candidates

    def extract_patterns(
        self, tree: tree_sitter.Tree, source_bytes: bytes, path: str
    ) -> list[dict[str, Any]]:
        """Extract framework patterns: Express routes, Next.js routes, CommonJS entrypoints."""
        patterns: list[dict[str, Any]] = []

        def _get_node_text(node: tree_sitter.Node) -> str:
            return source_bytes[node.start_byte : node.end_byte].decode(
                "utf-8", errors="replace"
            )

        # 1. Next.js Routes (App Router or Pages Router)
        router_kind, route_url = extract_nextjs_route_path(path)
        if router_kind == "app" and route_url:
            # Check exported HTTP methods in App Router
            for node in tree.root_node.children:
                if node.type == "export_statement":
                    fn_decl = None
                    for c in node.children:
                        if c.type in (
                            "function_declaration",
                            "generator_function_declaration",
                        ):
                            fn_decl = c
                            break
                    if fn_decl:
                        name_node = fn_decl.child_by_field_name("name")
                        if name_node:
                            method_name = _get_node_text(name_node).strip()
                            if method_name in (
                                "GET",
                                "POST",
                                "PUT",
                                "DELETE",
                                "PATCH",
                                "HEAD",
                                "OPTIONS",
                            ):
                                patterns.append(
                                    {
                                        "kind": "route",
                                        "name": f"{method_name} {route_url}",
                                        "url_path": route_url,
                                        "methods": [method_name],
                                        "handler": method_name,
                                        "range": [
                                            fn_decl.start_point.row + 1,
                                            fn_decl.start_point.column,
                                            fn_decl.end_point.row + 1,
                                            fn_decl.end_point.column,
                                        ],
                                        "raw_text": f"export {method_name} route",
                                    }
                                )

        elif router_kind == "pages" and route_url:
            # Pages Router API route
            handler_name = "handler"
            for node in tree.root_node.children:
                if node.type == "export_statement":
                    for c in node.children:
                        if c.type in ("function_declaration", "class_declaration"):
                            n = c.child_by_field_name("name")
                            if n:
                                handler_name = _get_node_text(n).strip()
                                break

            patterns.append(
                {
                    "kind": "route",
                    "name": f"ALL {route_url}",
                    "url_path": route_url,
                    "methods": ["GET", "POST", "PUT", "DELETE"],
                    "handler": handler_name,
                    "range": [1, 0, 1, 0],
                    "raw_text": f"pages/api route {route_url}",
                }
            )

        # 2. Express Route and Entrypoint Detection via AST walk
        def _walk_patterns(node: tree_sitter.Node):
            # Express: app.get(), router.post(), app.use(), etc.
            if node.type == "call_expression":
                fn_node = node.child_by_field_name("function")
                args_node = node.child_by_field_name("arguments")
                if fn_node and args_node and fn_node.type == "member_expression":
                    prop = fn_node.child_by_field_name("property")
                    if prop:
                        method_raw = _get_node_text(prop).strip().lower()
                        if method_raw in (
                            "get",
                            "post",
                            "put",
                            "delete",
                            "patch",
                            "use",
                        ):
                            named_args = [
                                c
                                for c in args_node.children
                                if c.type not in ("(", ")", ",")
                            ]
                            if named_args and named_args[0].type == "string":
                                url_path = clean_string_literal(
                                    _get_node_text(named_args[0])
                                )
                                handler = None
                                middlewares: list[str] = []
                                if len(named_args) > 1:
                                    last_arg = named_args[-1]
                                    if last_arg.type == "identifier":
                                        handler = _get_node_text(last_arg).strip()
                                    elif last_arg.type == "arrow_function":
                                        handler = f"inline_{url_path.strip('/').replace('/', '_')}"
                                        patterns.append({
                                            "kind": "function",
                                            "name": handler,
                                            "inline_handler": True,
                                            "range": [
                                                last_arg.start_point.row + 1,
                                                last_arg.start_point.column,
                                                last_arg.end_point.row + 1,
                                                last_arg.end_point.column,
                                            ],
                                            "raw_text": _get_node_text(last_arg).strip(),
                                        })
                                    # Middleware = middle args that are identifiers or calls
                                    middlewares = [
                                        _get_node_text(a).strip()
                                        for a in named_args[1:-1]
                                        if a.type in ("identifier", "call_expression")
                                    ]

                                method_name = (
                                    method_raw.upper()
                                    if method_raw != "use"
                                    else "USE"
                                )
                                patterns.append(
                                    {
                                        "kind": "route",
                                        "name": f"{method_name} {url_path}",
                                        "url_path": url_path,
                                        "methods": [method_name],
                                        "handler": handler,
                                        "middleware": middlewares,
                                        "range": [
                                            node.start_point.row + 1,
                                            node.start_point.column,
                                            node.end_point.row + 1,
                                            node.end_point.column,
                                        ],
                                        "raw_text": _get_node_text(node).strip(),
                                    }
                                )

            # CommonJS entrypoint: if (require.main === module)
            elif node.type == "if_statement":
                cond = node.child_by_field_name("condition")
                if cond:
                    cond_text = _get_node_text(cond)
                    if "require.main === module" in cond_text or "require.main == module" in cond_text:
                        patterns.append(
                            {
                                "kind": "entrypoint",
                                "name": "main",
                                "target": None,
                                "range": [
                                    node.start_point.row + 1,
                                    node.start_point.column,
                                    node.end_point.row + 1,
                                    node.end_point.column,
                                ],
                                "raw_text": cond_text.strip(),
                            }
                        )

            for child in node.children:
                _walk_patterns(child)

        _walk_patterns(tree.root_node)

        # 3. Generic named registration -> command (no SDK/verb list).
        # Commands live in the CLI layer (structural path rule); other files
        # with string+handler calls (events, logs, cron) are not commands.
        is_cli_file = (
            "cli/commands/" in path.replace("\\", "/") or
            path.replace("\\", "/").startswith("bin/")
        )
        route_lines: set[int] = {p["range"][0] for p in patterns if p["kind"] == "route"}

        def _find_handler(named_args: list[tree_sitter.Node]) -> str | None:
            for a in named_args:
                if a.type in ("identifier", "arrow_function", "function_expression", "function"):
                    return _get_node_text(a).strip().split(".")[0]
                if a.type == "call_expression":
                    f = a.child_by_field_name("function")
                    if f:
                        return _get_node_text(f).strip().split(".")[0]
            return None

        def _walk_commands(node: tree_sitter.Node):
            if is_cli_file and node.type == "call_expression":
                line = node.start_point.row + 1
                if line not in route_lines:
                    fn_node = node.child_by_field_name("function")
                    args_node = node.child_by_field_name("arguments")
                    if fn_node and args_node:
                        named_args = [
                            c for c in args_node.children
                            if c.type not in ("(", ")", ",")
                        ]
                        # Name = first string literal argument.
                        name = None
                        if named_args and named_args[0].type == "string":
                            name = clean_string_literal(_get_node_text(named_args[0]))
                        # Filter out option strings and non-command names
                        if name and (name.startswith("-") or " " in name or not name.replace("-", "").replace("_", "").isalnum()):
                            name = None
                        # Chained form: X.command("name").action(handler) —
                        # the outer call has the handler, the inner has the name.
                        if name is None and fn_node.type == "member_expression":
                            obj = fn_node.child_by_field_name("object")
                            if obj and obj.type == "call_expression":
                                inner_fn = obj.child_by_field_name("function")
                                inner_args = obj.child_by_field_name("arguments")
                                if inner_fn and inner_args:
                                    inner_named = [
                                        c for c in inner_args.children
                                        if c.type not in ("(", ")", ",")
                                    ]
                                    if inner_named and inner_named[0].type == "string":
                                        name = clean_string_literal(_get_node_text(inner_named[0]))
                        handler = _find_handler(named_args)
                        if name and handler:
                            patterns.append({
                                "kind": "command",
                                "name": name,
                                "handler": handler,
                                "range": [line, node.start_point.column,
                                          node.end_point.row + 1, node.end_point.column],
                                "raw_text": _get_node_text(node).strip(),
                            })
            for child in node.children:
                _walk_commands(child)

        _walk_commands(tree.root_node)

        # 4. Source-level entrypoint: shebang or explicit parse() invocation.
        source_text = source_bytes.decode("utf-8", errors="replace")
        if source_text.startswith("#!") or re.search(r"\b(program|app|cli)\.parse\s*\(", source_text):
            # Link 'starts' to the top-level function in this file if present.
            target = None
            for n in tree.root_node.children:
                if n.type in ("function_declaration", "lexical_declaration"):
                    name_node = n.child_by_field_name("name")
                    if name_node:
                        target = _get_node_text(name_node).strip()
                        break
                    # const main = () => ...
                    for c in n.named_children:
                        if c.type == "variable_declarator":
                            nn = c.child_by_field_name("name")
                            if nn:
                                target = _get_node_text(nn).strip()
                                break
            patterns.append({
                "kind": "entrypoint",
                "name": "main",
                "target": target,
                "range": [1, 0, 1, 0],
                "raw_text": "source-level entrypoint",
            })

        # Sort patterns deterministically by line number
        patterns.sort(key=lambda p: (p["range"][0], p["name"]))
        return patterns
