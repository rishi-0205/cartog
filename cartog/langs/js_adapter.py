"""JavaScript and TypeScript Language Adapter using tree-sitter."""

import json
import os
from pathlib import Path
import re
from typing import Any, NamedTuple, Optional
import tree_sitter
import tree_sitter_javascript
import tree_sitter_typescript

from cartog.langs.base import (
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


def load_json_with_comments(path: Path) -> Optional[dict[str, Any]]:
    """Load JSON file tolerating single-line comments and trailing commas."""
    if not path.is_file():
        return None
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        # Strip single-line comments (// ...)
        content = re.sub(r"//.*", "", content)
        # Strip trailing commas before closing braces/brackets
        content = re.sub(r",(\s*[}\]])", r"\1", content)
        return json.loads(content)
    except Exception:
        return None


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


def path_to_js_module_name(rel_path: str, roots: Optional[list[str]] = None) -> str:
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


def extract_nextjs_route_path(file_path: str) -> tuple[Optional[str], Optional[str]]:
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
        self._tsconfig_cache: dict[str, Optional[dict[str, Any]]] = {}
        self._workspaces_cache: Optional[dict[str, dict[str, str]]] = None

    def grammar_for(self, path: Path) -> tree_sitter.Language:
        suffix = path.suffix.lower()
        if suffix == ".tsx":
            return self._lang_tsx
        elif suffix == ".ts":
            return self._lang_ts
        return self._lang_js

    def parse(
        self, source_bytes: bytes, path: Optional[Path | str] = None
    ) -> tree_sitter.Tree:
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
            var_name: Optional[str] = None

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
                parent_class: Optional[str] = None
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

                for c in node.children:
                    if c.type == "import_clause":
                        for gc in c.children:
                            if gc.type == "identifier":
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
                        line=node.start_point.row,
                        level=_count_level(specifier),
                        raw_text=raw_text,
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

                    for c in node.children:
                        if c.type == "export_clause":
                            for sc in c.children:
                                if sc.type == "export_specifier":
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
                            line=node.start_point.row,
                            level=_count_level(specifier),
                            raw_text=raw_text,
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
                                    line=node.start_point.row,
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

    def _get_tsconfig(self, root_dir: str, target_path: str = ".") -> Optional[dict[str, Any]]:
        """Load and cache tsconfig.json or jsconfig.json for a given directory."""
        cache_key = f"{target_path}::{root_dir}"
        if cache_key in self._tsconfig_cache:
            return self._tsconfig_cache[cache_key]

        target_p = Path(target_path) if target_path != "." else Path("")
        base_p = (target_p / root_dir) if root_dir != "." else target_p
        ts_p = base_p / "tsconfig.json"
        js_p = base_p / "jsconfig.json"

        data = None
        if ts_p.is_file():
            data = load_json_with_comments(ts_p)
        elif js_p.is_file():
            data = load_json_with_comments(js_p)

        self._tsconfig_cache[cache_key] = data
        return data

    def _discover_workspace_packages(
        self, project_context: ProjectContext
    ) -> dict[str, dict[str, str]]:
        """Discover packages in monorepo workspaces and map package name -> info."""
        target_path = getattr(project_context, "target_path", ".") or "."
        if self._workspaces_cache is not None and target_path in self._workspaces_cache:
            return self._workspaces_cache[target_path]

        packages: dict[str, dict[str, str]] = {}
        roots = getattr(project_context, "roots", ["."]) or ["."]
        target_p = Path(target_path) if target_path != "." else Path("")

        for r in roots:
            base_p = (target_p / r) if r != "." else target_p
            pkg_json = base_p / "package.json"
            if not pkg_json.is_file():
                continue

            data = load_json_with_comments(pkg_json)
            if not data or not isinstance(data, dict):
                continue

            workspaces = data.get("workspaces", [])
            if isinstance(workspaces, dict):
                workspaces = workspaces.get("packages", [])
            if not isinstance(workspaces, list):
                continue

            for pattern in workspaces:
                # e.g. "packages/*"
                clean_pat = pattern.rstrip("/")
                if clean_pat.endswith("/*"):
                    parent_dir = base_p / clean_pat[:-2]
                    if parent_dir.is_dir():
                        try:
                            for child in parent_dir.iterdir():
                                if child.is_dir():
                                    child_pkg = child / "package.json"
                                    if child_pkg.is_file():
                                        c_data = load_json_with_comments(child_pkg)
                                        if c_data and "name" in c_data:
                                            try:
                                                rel_pkg_dir = child.relative_to(target_p).as_posix()
                                            except ValueError:
                                                rel_pkg_dir = child.as_posix()
                                            packages[c_data["name"]] = {
                                                "dir": rel_pkg_dir,
                                                "main": c_data.get("main", "src/index.ts"),
                                                "module": c_data.get("module", ""),
                                            }
                        except Exception:
                            pass
                else:
                    target_dir = base_p / clean_pat
                    child_pkg = target_dir / "package.json"
                    if child_pkg.is_file():
                        c_data = load_json_with_comments(child_pkg)
                        if c_data and "name" in c_data:
                            try:
                                rel_pkg_dir = target_dir.relative_to(target_p).as_posix()
                            except ValueError:
                                rel_pkg_dir = target_dir.as_posix()
                            packages[c_data["name"]] = {
                                "dir": rel_pkg_dir,
                                "main": c_data.get("main", "src/index.ts"),
                                "module": c_data.get("module", ""),
                            }

        if self._workspaces_cache is None:
            self._workspaces_cache = {}
        self._workspaces_cache[target_path] = packages
        return packages

    def _resolve_relative(
        self, specifier: str, from_file: str, all_files: set[str]
    ) -> Optional[str]:
        """Resolve a relative import specifier with JS/TS extension rewriting and index probing."""
        from_dir = Path(from_file).parent
        # Remove leading ./ for clean joining
        clean_spec = specifier
        target_base = (from_dir / clean_spec)

        # Probing helper
        def _probe(base_path: Path) -> Optional[str]:
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
            cfg = self._get_tsconfig(r, target_path=target_path)
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

        # 3. Monorepo workspace package resolution
        ws_pkgs = self._discover_workspace_packages(project_context)
        for pkg_name, pkg_info in ws_pkgs.items():
            if specifier == pkg_name:
                pkg_dir = pkg_info["dir"]
                main_file = pkg_info.get("main", "src/index.ts")
                target = Path(pkg_dir) / main_file
                res = self._probe_candidate(target, all_files)
                if res:
                    return res
                # Fallback to standard index files in pkg_dir or pkg_dir/src
                for sub in ("src/index.ts", "src/index.js", "index.ts", "index.js"):
                    fb = Path(pkg_dir) / sub
                    if fb.as_posix() in all_files:
                        return fb.as_posix()
            elif specifier.startswith(pkg_name + "/"):
                sub_path = specifier[len(pkg_name) + 1 :]
                target = Path(pkg_info["dir"]) / sub_path
                res = self._probe_candidate(target, all_files)
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

    def _probe_candidate(self, cand_base: Path, all_files: set[str]) -> Optional[str]:
        """Probe a candidate file path with standard extensions and directory indexes."""
        try:
            norm = os.path.normpath(cand_base.as_posix()).replace("\\", "/")
        except Exception:
            norm = cand_base.as_posix()
        if norm.startswith("./"):
            norm = norm[2:]

        if norm in all_files:
            return norm

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
                                if len(named_args) > 1:
                                    last_arg = named_args[-1]
                                    if last_arg.type == "identifier":
                                        handler = _get_node_text(last_arg).strip()

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

        # Sort patterns deterministically by line number
        patterns.sort(key=lambda p: (p["range"][0], p["name"]))
        return patterns
