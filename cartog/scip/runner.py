"""SCIP indexer execution, decoding, occurrence extraction, and call graph resolution."""

import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cartog.core.config import SCHEMA_VERSION
from cartog.core.diagnostics import get_logger
from cartog.core.model import SourceRange
from cartog.core.proc import run as run_process
from cartog.parse.base import SymbolRecord
from cartog.scip.scip_pb2 import Index

logger = get_logger()


@dataclass
class ScipOccurrence:
    """Decoded SCIP occurrence within a document."""
    symbol: str
    range: SourceRange
    is_definition: bool
    roles: int = 0
    syntax_kind: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON form of the occurrence."""
        return {
            "symbol": self.symbol,
            "range": self.range.to_list(),
            "roles": self.roles,
            "is_definition": self.is_definition,
            "syntax_kind": self.syntax_kind,
        }


@dataclass
class ScipDocument:
    """Decoded SCIP document representing a single source file."""
    relative_path: str
    language: str
    definitions: list[ScipOccurrence] = field(default_factory=list)
    references: list[ScipOccurrence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON form of the document."""
        return {
            "relative_path": self.relative_path,
            "language": self.language,
            "definitions": [d.to_dict() for d in self.definitions],
            "references": [r.to_dict() for r in self.references],
        }


@dataclass
class ScipRelationship:
    """Relationship between symbols in SCIP (e.g. implementation, reference)."""
    symbol: str
    target_symbol: str
    is_implementation: bool = False
    is_reference: bool = False
    is_type_definition: bool = False
    is_definition: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON form of the relationship."""
        return {
            "symbol": self.symbol,
            "target_symbol": self.target_symbol,
            "is_implementation": self.is_implementation,
            "is_reference": self.is_reference,
            "is_type_definition": self.is_type_definition,
            "is_definition": self.is_definition,
        }


@dataclass
class ScipIndexResult:
    """Aggregated SCIP indexing and decoding result."""
    ran: bool
    indexer: str | None = None
    documents: list[ScipDocument] = field(default_factory=list)
    error: str | None = None
    definitions_by_symbol: dict[str, tuple[str, SourceRange]] = field(default_factory=dict)
    relationships: list[ScipRelationship] = field(default_factory=list)
    interpreter_path: str | None = None
    python_version: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON form of the decoded index result."""
        return {
            "schema_version": SCHEMA_VERSION,
            "meta": {
                "ran": self.ran,
                "indexer": self.indexer,
                "documents_count": len(self.documents),
                "error": self.error,
                "interpreter_path": self.interpreter_path,
                "python_version": self.python_version,
                "warnings": self.warnings,
            },
            "documents": [d.to_dict() for d in self.documents],
            "relationships": [r.to_dict() for r in self.relationships],
        }


@dataclass
class CallEdgeCandidate:
    """Resolved call/reference/override candidate from caller to callee."""
    caller_path: str
    caller_symbol: str | None
    callee_path: str
    callee_symbol: str
    evidence: list[str] = field(default_factory=list)
    count: int = 1
    caller_qualified_name: str | None = None
    callee_qualified_name: str | None = None
    kind: str = "calls"
    ref_kind: str | None = None
    confidence: str = "resolved"


def normalize_scip_range(raw_range: list[int]) -> SourceRange:
    """Convert SCIP 3-tuple or 4-tuple range into a standard 1-based SourceRange."""
    if len(raw_range) == 3:
        line, start_col, end_col = raw_range
        return SourceRange(start_line=line + 1, start_col=start_col, end_line=line + 1, end_col=end_col)
    elif len(raw_range) >= 4:
        return SourceRange(
            start_line=raw_range[0] + 1,
            start_col=raw_range[1],
            end_line=raw_range[2] + 1,
            end_col=raw_range[3],
        )
    return SourceRange(start_line=1, start_col=0, end_line=1, end_col=0)


def decode_scip_index(scip_path: str | Path, target_path: str | Path | None = None) -> ScipIndexResult:
    """Read a binary index.scip file and extract structured documents, definitions, and references."""
    p = Path(scip_path)
    if not p.is_file():
        return ScipIndexResult(ran=False, error=f"SCIP index file not found: {p}")

    index = Index()
    try:
        with open(p, "rb") as f:
            index.ParseFromString(f.read())
    except Exception as e:
        return ScipIndexResult(ran=False, error=f"Failed to decode index.scip: {e}")

    docs: list[ScipDocument] = []
    defs_by_symbol: dict[str, tuple[str, SourceRange]] = {}
    relationships: list[ScipRelationship] = []
    target_p = Path(target_path) if target_path else None

    for doc in index.documents:
        rel_path = doc.relative_path.replace("\\", "/")
        scip_doc = ScipDocument(relative_path=rel_path, language=doc.language)

        doc_lines: list[str] | None = None
        if target_p:
            src_f = target_p / rel_path
            if src_f.is_file():
                try:
                    doc_lines = src_f.read_text(encoding="utf-8", errors="ignore").splitlines()
                except Exception:
                    doc_lines = None
        if doc_lines is None:
            src_f = Path(rel_path)
            if src_f.is_file():
                try:
                    doc_lines = src_f.read_text(encoding="utf-8", errors="ignore").splitlines()
                except Exception:
                    doc_lines = None

        for s in doc.symbols:
            for r in s.relationships:
                relationships.append(
                    ScipRelationship(
                        symbol=s.symbol,
                        target_symbol=r.symbol,
                        is_implementation=bool(r.is_implementation),
                        is_reference=bool(r.is_reference),
                        is_type_definition=bool(r.is_type_definition),
                        is_definition=bool(r.is_definition),
                    )
                )

        # Map local imported symbols to synthetic module-qualified symbols
        local_symbol_map: dict[str, tuple[str, int]] = {}
        for occ in doc.occurrences:
            if (occ.symbol_roles & 0x8) and occ.symbol.startswith("local "):
                line = occ.range[0]
                mod_occs = [
                    o for o in doc.occurrences
                    if o.range[0] == line and (o.symbol_roles & 0x8) and not o.symbol.startswith("local ")
                ]
                if mod_occs:
                    mod_sym = mod_occs[0].symbol
                    sym_name = None
                    if doc_lines is not None and line < len(doc_lines) and len(occ.range) >= 3:
                        c1, c2 = occ.range[1], occ.range[2]
                        if c1 < c2 <= len(doc_lines[line]):
                            candidate = doc_lines[line][c1:c2].strip()
                            if candidate.isidentifier():
                                sym_name = candidate
                    if not sym_name:
                        s_matches = [s for s in doc.symbols if s.symbol == occ.symbol]
                        if s_matches and s_matches[0].documentation:
                            m_doc = re.search(r"(?:def|class|variable|constant|function)\s+([a-zA-Z0-9_]+)", s_matches[0].documentation[0])
                            if m_doc:
                                sym_name = m_doc.group(1)
                    if sym_name:
                        parts = mod_sym.split(" ", 4)
                        if len(parts) == 5:
                            mod_desc = parts[4].rstrip(":")
                            synth_sym = f"{parts[0]} {parts[1]} {parts[2]} {parts[3]} {mod_desc}:{sym_name}"
                            local_symbol_map[occ.symbol] = (synth_sym, line)

        for occ in doc.occurrences:
            sym = occ.symbol
            if sym.startswith("local "):
                if sym in local_symbol_map:
                    synth_sym, imp_line = local_symbol_map[sym]
                    if occ.range[0] != imp_line:
                        sym = synth_sym
                    else:
                        continue
                else:
                    continue

            rng = normalize_scip_range(list(occ.range))
            is_def = bool(occ.symbol_roles & 0x1)

            rec = ScipOccurrence(
                symbol=sym,
                range=rng,
                is_definition=is_def,
                roles=occ.symbol_roles,
                syntax_kind=str(occ.syntax_kind) if occ.syntax_kind else None,
            )

            if is_def:
                scip_doc.definitions.append(rec)
                if sym not in defs_by_symbol:
                    defs_by_symbol[sym] = (rel_path, rng)
            else:
                scip_doc.references.append(rec)

        docs.append(scip_doc)

    return ScipIndexResult(
        ran=True,
        documents=docs,
        definitions_by_symbol=defs_by_symbol,
        relationships=relationships,
    )


def get_indexer_env(
    indexer_name: str,
    target_p: Path | None = None,
    python_path: str | None = None,
    roots: list[str] | None = None,
) -> dict[str, str]:
    """Return subprocess environment with Windows Node compatibility shims, interpreter on PATH, and PYTHONPATH."""
    env = os.environ.copy()
    if sys.platform == "win32" and indexer_name == "scip-python":
        shim_path = (Path(__file__).parent / "windows_shim.js").resolve()
        if shim_path.is_file():
            current_options = env.get("NODE_OPTIONS", "")
            shim_flag = f'-r "{shim_path.as_posix()}"'
            if shim_flag not in current_options:
                env["NODE_OPTIONS"] = f"{current_options} {shim_flag}".strip()

    if python_path:
        py_p = Path(python_path).resolve()
        py_dir = str(py_p.parent)
        env["PATH"] = f"{py_dir}{os.pathsep}{env.get('PATH', '')}"
        if py_p.parent.name.lower() in ("scripts", "bin"):
            env["VIRTUAL_ENV"] = str(py_p.parent.parent)

    if target_p:
        resolved_target = target_p.resolve()
        python_paths = [str(resolved_target)]
        for r in (roots or ["."]):
            if r != ".":
                r_dir = (resolved_target / r).resolve()
                if r_dir.is_dir():
                    python_paths.append(str(r_dir))
        current_pythonpath = env.get("PYTHONPATH", "")
        if current_pythonpath:
            python_paths.append(current_pythonpath)
        env["PYTHONPATH"] = os.pathsep.join(python_paths)

    return env


def run_scip_indexer(
    target_path: str | Path,
    out_dir: str | Path,
    language: str = "python",
    project_name: str | None = None,
    timeout_sec: int = 120,
    python_path: str | None = None,
    roots: list[str] | None = None,
) -> ScipIndexResult:
    """Run external SCIP indexer with pre-checks, timeouts, and graceful error handling."""
    target_p = Path(target_path).resolve()
    out_p = Path(out_dir).resolve()

    indexer_cmd: list[str] = []
    indexer_name = "scip-python" if language == "python" else "scip-typescript"

    def _fail(reason: str) -> ScipIndexResult:
        try:
            out_p.mkdir(parents=True, exist_ok=True)
            (out_p / "scip_error.log").write_text(reason, encoding="utf-8")
        except Exception:
            pass
        return ScipIndexResult(ran=False, indexer=indexer_name, error=reason)

    is_win = sys.platform.startswith("win")
    which_bin = shutil.which(indexer_name)
    if not which_bin:
        reason = f"Indexer '{indexer_name}' not found on PATH."
        logger.warning(reason)
        return _fail(reason)

    resolved_python: str | None = None
    python_version: str | None = None
    if language == "python":
        if python_path:
            resolved_python = str(Path(python_path).resolve())
        else:
            # Check target repo virtualenv
            venv_scripts = "Scripts" if is_win else "bin"
            py_exe = "python.exe" if is_win else "python"
            target_venv_py = target_p / ".venv" / venv_scripts / py_exe
            if not target_venv_py.is_file():
                target_venv_py = target_p / "venv" / venv_scripts / py_exe
            if target_venv_py.is_file():
                resolved_python = str(target_venv_py.resolve())
            else:
                resolved_python = sys.executable

        # Query version of resolved Python interpreter
        try:
            v_res = run_process(
                [resolved_python, "--version"], timeout=5, allow_python=True
            )
            python_version = (v_res.stdout.strip() or v_res.stderr.strip()) or None
        except Exception:
            python_version = None

        # Respect existing pyright configuration in repo without modifying it
        if (target_p / "pyrightconfig.json").is_file():
            logger.info("Respected existing pyrightconfig.json in analyzed repository.")
        elif (target_p / "pyproject.toml").is_file():
            try:
                pyproj_txt = (target_p / "pyproject.toml").read_text(encoding="utf-8-sig", errors="ignore")
                if "[tool.pyright]" in pyproj_txt:
                    logger.info("Respected existing [tool.pyright] in pyproject.toml.")
            except Exception:
                pass

    env = get_indexer_env(indexer_name, target_p=target_p, python_path=resolved_python, roots=roots)

    # Pre-check execution (ensure indexer runs cleanly without crash)
    try:
        check_res = run_process(
            [indexer_name, "--version"],
            timeout=5,
            env=env,
        )
        if check_res.returncode != 0:
            full_err = check_res.stderr.strip() or check_res.stdout.strip()
            reason = f"Indexer '{indexer_name}' failed pre-check (exit code {check_res.returncode}): {full_err}"
            logger.warning(f"Indexer '{indexer_name}' failed pre-check (exit code {check_res.returncode}): {full_err[:120]}")
            return _fail(reason)
    except Exception as e:
        reason = f"Indexer '{indexer_name}' pre-check raised exception: {e}"
        logger.warning(reason)
        return _fail(reason)

    # Root hash directory in out_dir/.cartog/scip/<hash>/
    path_hash = hashlib.sha1(target_p.as_posix().encode("utf-8")).hexdigest()[:12]
    scip_out_dir = out_p / ".cartog" / "scip" / path_hash
    scip_out_dir.mkdir(parents=True, exist_ok=True)
    scip_out_file = scip_out_dir / "index.scip"

    proj = project_name or target_p.name

    has_node_modules = (target_p / "node_modules").is_dir()
    if language != "python" and (target_p / "package.json").is_file() and not has_node_modules:
        logger.info(
            f"Notice: 'node_modules' directory not found in '{target_p.as_posix()}'. "
            "If indexing fails, run 'npm install' in the project directory."
        )

    target_str = str(target_p) if is_win else target_p.as_posix()
    out_str = str(scip_out_file) if is_win else scip_out_file.as_posix()

    if language == "python":
        indexer_cmd = [
            indexer_name,
            "index",
            "--cwd",
            target_str,
            "--project-name",
            proj,
            "--output",
            out_str,
        ]
    else:
        indexer_cmd = [
            indexer_name,
            "index",
            "--infer-tsconfig",
            "--cwd",
            target_str,
            "--output",
            out_str,
        ]

    logger.info(f"Running SCIP indexer: {' '.join(indexer_cmd)}")

    try:
        proc = run_process(
            indexer_cmd,
            cwd=target_p,
            timeout=timeout_sec,
            env=env,
        )
        if proc.timed_out:
            reason = f"SCIP indexer timed out after {timeout_sec}s."
            logger.warning(reason)
            return _fail(reason)
        if proc.returncode != 0:
            full_err = proc.stderr.strip() or proc.stdout.strip()
            reason = f"SCIP indexer exited with code {proc.returncode}: {full_err}"
            if language != "python" and not has_node_modules:
                reason += " (Hint: 'node_modules' not found. Run 'npm install' in target directory.)"
            logger.warning(f"SCIP indexer failed (exit code {proc.returncode}): {full_err[:120]}")
            return _fail(reason)

        indexer_warnings: list[str] = []
        if proc.stderr:
            for line in proc.stderr.splitlines():
                l_clean = line.strip()
                if l_clean and any(k in l_clean.lower() for k in ("warning", "error", "toml", "warn")):
                    indexer_warnings.append(l_clean)

        # Fallback check if indexer placed output in local index.scip
        local_index = target_p / "index.scip"
        if not scip_out_file.is_file() and local_index.is_file():
            shutil.move(local_index, scip_out_file)

        if not scip_out_file.is_file():
            reason = "SCIP indexer completed but output index.scip was not produced."
            logger.warning(reason)
            return _fail(reason)

    except Exception as e:
        reason = f"SCIP indexer execution error: {e}"
        logger.warning(reason)
        return _fail(reason)

    result = decode_scip_index(scip_out_file, target_path=target_p)
    result.indexer = indexer_name
    result.interpreter_path = resolved_python
    result.python_version = python_version
    result.warnings = indexer_warnings[:20]
    return result


def find_enclosing_symbol(
    range_target: SourceRange, symbols: list[SymbolRecord]
) -> SymbolRecord | None:
    """Find innermost function, method, or class enclosing the given range."""
    best_match: SymbolRecord | None = None
    best_span: int | None = None

    t_start = (range_target.start_line, range_target.start_col)
    t_end = (range_target.end_line, range_target.end_col)

    for sym in symbols:
        sym_start = (sym.start_line, sym.start_col)
        sym_end = (sym.end_line, sym.end_col)

        if sym_start <= t_start and sym_end >= t_end:
            span = (sym.end_line - sym.start_line) * 10000 + (sym.end_col - sym.start_col)
            if best_span is None or span < best_span:
                best_match = sym
                best_span = span

    return best_match


def classify_occurrence(tree: Any, line: int, col: int, language: str = "python") -> tuple[str, str | None]:
    """Determine (edge_kind, ref_kind) for an AST occurrence at 1-based (line, col)."""
    if not tree:
        return ("calls", None)

    point = (max(0, line - 1), max(0, col))
    node = tree.root_node.descendant_for_point_range(point, point)
    if not node:
        return ("calls", None)

    curr = node
    while curr:
        t = curr.type
        # 1. Decorators
        if t == "decorator":
            return ("references", "decorator")
        # 2. Exceptions
        if t in ("except_clause", "raise_statement", "throw_statement", "catch_clause"):
            return ("references", "exception")
        # 3. Class inheritance
        if t in ("class_heritage", "extends_clause", "implements_clause"):
            return ("references", "inheritance")
        if t == "class_definition":
            args = curr.child_by_field_name("superclasses")
            if args and args.start_byte <= node.start_byte <= args.end_byte:
                return ("references", "inheritance")
        # 4. Type annotations
        if t in ("type", "type_annotation", "type_arguments", "type_parameter"):
            return ("references", "type")
        # 5. Calls and callback arguments
        if t in ("call", "call_expression"):
            func = curr.child_by_field_name("function")
            if func:
                func_text = func.text.decode("utf-8", errors="ignore")
                if func_text in ("isinstance", "issubclass"):
                    return ("references", "isinstance")
            args = curr.child_by_field_name("arguments")
            if args and args.start_byte <= node.start_byte <= args.end_byte:
                return ("references", "callback")
            if func and func.start_byte <= node.start_byte <= func.end_byte:
                return ("calls", None)
            return ("calls", None)
        if t == "binary_expression":
            op = curr.child_by_field_name("operator")
            if op and op.text.decode("utf-8", errors="ignore") == "instanceof":
                return ("references", "isinstance")

        curr = curr.parent

    return ("references", "other")


def link_calls(
    scip_result: ScipIndexResult,
    symbols_by_file: dict[str, list[SymbolRecord]],
    target_path: str = ".",
    roots: list[str] | None = None,
    language: str = "python",
    ignored_paths: set[str] | None = None,
    ignore_metrics: Any | None = None,
) -> list[CallEdgeCandidate]:
    """Map reference occurrences to caller and callee functions, constructing CallEdgeCandidates."""
    candidates_map: dict[tuple[str, str | None, str, str | None, str, str | None], CallEdgeCandidate] = {}

    target_p = Path(target_path).resolve() if target_path != "." else Path("")
    resolved_roots = roots or ["."]
    ignored = ignored_paths or set()

    # Initialize tree-sitter parser for occurrence classification
    trees: dict[str, Any] = {}
    parser = None
    try:
        if language == "python":
            import tree_sitter
            import tree_sitter_python
            py_lang = tree_sitter.Language(tree_sitter_python.language())
            parser = tree_sitter.Parser(py_lang)
        elif language in ("javascript", "typescript"):
            import tree_sitter
            import tree_sitter_typescript
            ts_lang = tree_sitter.Language(tree_sitter_typescript.language_typescript())
            parser = tree_sitter.Parser(ts_lang)
    except Exception as e:
        logger.debug(f"Could not initialize tree-sitter parser: {e}")

    def _get_tree(doc_path: str) -> Any | None:
        if not parser:
            return None
        if doc_path not in trees:
            f_path = (target_p / doc_path) if target_p != Path("") else Path(doc_path)
            if f_path.is_file():
                try:
                    trees[doc_path] = parser.parse(f_path.read_bytes())
                except Exception:
                    trees[doc_path] = None
            else:
                trees[doc_path] = None
        return trees.get(doc_path)

    # Candidate anchored prefixes derived from detected roots
    candidate_prefixes: set[str] = set()
    for r in resolved_roots:
        r_norm = r.replace("\\", "/").strip("/")
        if r_norm and r_norm != ".":
            candidate_prefixes.add(r_norm.replace("/", ".") + ".")
            for s in ("src", "lib"):
                if (target_p / r_norm / s).is_dir():
                    candidate_prefixes.add(f"{r_norm}/{s}".replace("/", ".") + ".")
        else:
            for s in ("src", "lib"):
                if (target_p / s).is_dir():
                    candidate_prefixes.add(f"{s}.")

    # Build reconciled definition index by normalized descriptor with anchored prefix
    reconciled_defs: dict[tuple[str, str], tuple[str, str, SourceRange]] = {}
    for sym, (def_path, def_range) in scip_result.definitions_by_symbol.items():
        parts = sym.split(" ", 4)
        if len(parts) == 5:
            pkg_name = parts[2]
            desc = parts[4]
            reconciled_defs[(pkg_name, desc)] = (sym, def_path, def_range)
            for pfx in candidate_prefixes:
                prefix_backtick = f"`{pfx}"
                if desc.startswith(prefix_backtick):
                    desc_norm = "`" + desc[len(prefix_backtick):]
                    reconciled_defs[(pkg_name, desc_norm)] = (sym, def_path, def_range)
                    if desc_norm.startswith("`") and "`/" in desc_norm:
                        bare_desc = desc_norm[1:].replace("`/", "/")
                        reconciled_defs[(pkg_name, bare_desc)] = (sym, def_path, def_range)
                elif desc.startswith(pfx):
                    desc_norm = desc[len(pfx):]
                    reconciled_defs[(pkg_name, desc_norm)] = (sym, def_path, def_range)

    # Re-export tracking: Index re-exported symbols from barrel files (__init__.py, index.ts, index.js)
    for doc in scip_result.documents:
        doc_p = Path(doc.relative_path)
        if doc_p.name in ("__init__.py", "index.ts", "index.js", "index.tsx", "index.jsx"):
            parent_dir = doc_p.parent.as_posix()
            mod_variants = [parent_dir.replace("/", ".")]
            for pfx in candidate_prefixes:
                pfx_clean = pfx.rstrip(".")
                if mod_variants[0] == pfx_clean:
                    mod_variants.append("")
                elif mod_variants[0].startswith(f"{pfx_clean}."):
                    mod_variants.append(mod_variants[0][len(pfx_clean) + 1:])

            for ref in doc.references:
                target_entry = None
                if ref.symbol in scip_result.definitions_by_symbol:
                    target_entry = (ref.symbol, *scip_result.definitions_by_symbol[ref.symbol])
                else:
                    r_parts = ref.symbol.split(" ", 4)
                    if len(r_parts) == 5 and (r_parts[2], r_parts[4]) in reconciled_defs:
                        target_entry = reconciled_defs[(r_parts[2], r_parts[4])]

                if not target_entry:
                    continue

                target_sym, def_p, def_rng = target_entry
                r_parts = target_sym.split(" ", 4)
                if len(r_parts) != 5:
                    continue
                pkg = r_parts[2]
                desc = r_parts[4]
                m_sym = re.search(r"[\./#]([a-zA-Z0-9_]+)(?:\(\)|\.|#)*$", desc)
                name = m_sym.group(1) if m_sym else None
                if not name:
                    continue

                for mod in mod_variants:
                    if not mod:
                        continue
                    reconciled_defs[(pkg, f"{mod}/__init__:{name}")] = (target_sym, def_p, def_rng)
                    reconciled_defs[(pkg, f"`{mod}`/__init__:{name}")] = (target_sym, def_p, def_rng)
                    reconciled_defs[(pkg, f"{mod}:{name}")] = (target_sym, def_p, def_rng)
                    reconciled_defs[(pkg, f"`{mod}`:{name}")] = (target_sym, def_p, def_rng)
                    reconciled_defs[(pkg, f"{mod}/{name}().")] = (target_sym, def_p, def_rng)
                    reconciled_defs[(pkg, f"`{mod}`/{name}().")] = (target_sym, def_p, def_rng)
                    reconciled_defs[(pkg, f"{mod}/{name}#")] = (target_sym, def_p, def_rng)
                    reconciled_defs[(pkg, f"`{mod}`/{name}#")] = (target_sym, def_p, def_rng)
                    reconciled_defs[(pkg, f"{mod}/{name}")] = (target_sym, def_p, def_rng)
                    reconciled_defs[(pkg, f"`{mod}`/{name}")] = (target_sym, def_p, def_rng)

    # 1. Process document references
    for doc in scip_result.documents:
        caller_path = doc.relative_path
        if caller_path in ignored:
            continue

        caller_symbols = symbols_by_file.get(caller_path, [])
        doc_tree = _get_tree(caller_path)

        for ref in doc.references:
            callee_path = None
            def_range = None
            conf = "resolved"

            if ref.symbol in scip_result.definitions_by_symbol:
                callee_path, def_range = scip_result.definitions_by_symbol[ref.symbol]
            else:
                # Reconciliation fallback: match anchored descriptor, package name, and verify file exists in repo
                parts = ref.symbol.split(" ", 4)
                if len(parts) == 5:
                    ref_pkg = parts[2]
                    ref_desc = parts[4]
                    if (ref_pkg, ref_desc) in reconciled_defs:
                        _, callee_path, def_range = reconciled_defs[(ref_pkg, ref_desc)]
                        f_full = (target_p / callee_path) if target_p != Path("") else Path(callee_path)
                        if not f_full.is_file():
                            continue
                        conf = "reconciled"
                    else:
                        continue
                else:
                    continue

            if not callee_path:
                continue

            # Drop edge if callee is in an ignored file
            if callee_path in ignored:
                if ignore_metrics is not None and hasattr(ignore_metrics, "dropped_edges_count"):
                    ignore_metrics.dropped_edges_count += 1
                continue

            callee_symbols = symbols_by_file.get(callee_path, [])

            # Find enclosing caller and callee symbols
            caller_sym = find_enclosing_symbol(ref.range, caller_symbols)
            caller_sym_name = caller_sym.name if caller_sym else None
            caller_qual_name = caller_sym.qualified_name if caller_sym else None

            callee_sym = find_enclosing_symbol(def_range, callee_symbols)
            if not callee_sym:
                continue
            callee_sym_name = callee_sym.name
            callee_qual_name = callee_sym.qualified_name

            # Skip self-call in same function
            caller_identity = caller_qual_name or caller_sym_name
            callee_identity = callee_qual_name or callee_sym_name
            if caller_path == callee_path and caller_identity == callee_identity:
                continue

            edge_kind, ref_kind = classify_occurrence(
                doc_tree, ref.range.start_line, ref.range.start_col, language=language
            )

            evidence_str = f"{caller_path}:{ref.range.start_line}"
            key = (caller_path, caller_identity, callee_path, callee_identity, edge_kind, ref_kind)

            if key not in candidates_map:
                candidates_map[key] = CallEdgeCandidate(
                    caller_path=caller_path,
                    caller_symbol=caller_sym_name,
                    callee_path=callee_path,
                    callee_symbol=callee_sym_name,
                    evidence=[evidence_str],
                    count=1,
                    caller_qualified_name=caller_qual_name,
                    callee_qualified_name=callee_qual_name,
                    kind=edge_kind,
                    ref_kind=ref_kind,
                    confidence=conf,
                )
            else:
                c = candidates_map[key]
                c.count += 1
                if len(c.evidence) < 3 and evidence_str not in c.evidence:
                    c.evidence.append(evidence_str)
                if conf == "reconciled" and c.confidence != "reconciled":
                    c.confidence = "reconciled"

    # 2. Process SCIP relationships for overrides edges
    for rel in scip_result.relationships:
        if not rel.is_implementation:
            continue

        impl_path, impl_range = None, None
        if rel.symbol in scip_result.definitions_by_symbol:
            impl_path, impl_range = scip_result.definitions_by_symbol[rel.symbol]
        else:
            p_impl = rel.symbol.split(" ", 4)
            if len(p_impl) == 5 and (p_impl[2], p_impl[4]) in reconciled_defs:
                _, impl_path, impl_range = reconciled_defs[(p_impl[2], p_impl[4])]

        tgt_path, tgt_range = None, None
        rel_conf = "resolved"
        if rel.target_symbol in scip_result.definitions_by_symbol:
            tgt_path, tgt_range = scip_result.definitions_by_symbol[rel.target_symbol]
        else:
            p_tgt = rel.target_symbol.split(" ", 4)
            if len(p_tgt) == 5 and (p_tgt[2], p_tgt[4]) in reconciled_defs:
                _, tgt_path, tgt_range = reconciled_defs[(p_tgt[2], p_tgt[4])]
                rel_conf = "reconciled"

        if impl_path and tgt_path and impl_range and tgt_range:
            if impl_path in ignored:
                continue
            if tgt_path in ignored:
                if ignore_metrics is not None and hasattr(ignore_metrics, "dropped_edges_count"):
                    ignore_metrics.dropped_edges_count += 1
                continue

            f_impl = (target_p / impl_path) if target_p != Path("") else Path(impl_path)
            f_tgt = (target_p / tgt_path) if target_p != Path("") else Path(tgt_path)
            if not f_impl.is_file() or not f_tgt.is_file():
                continue

            impl_symbols = symbols_by_file.get(impl_path, [])
            impl_sym = find_enclosing_symbol(impl_range, impl_symbols)
            tgt_symbols = symbols_by_file.get(tgt_path, [])
            tgt_sym = find_enclosing_symbol(tgt_range, tgt_symbols)

            if impl_sym and tgt_sym:
                impl_id = impl_sym.qualified_name or impl_sym.name
                tgt_id = tgt_sym.qualified_name or tgt_sym.name
                key = (impl_path, impl_id, tgt_path, tgt_id, "overrides", None)
                if key not in candidates_map:
                    candidates_map[key] = CallEdgeCandidate(
                        caller_path=impl_path,
                        caller_symbol=impl_sym.name,
                        callee_path=tgt_path,
                        callee_symbol=tgt_sym.name,
                        evidence=[f"{impl_path}:{impl_range.start_line}"],
                        count=1,
                        caller_qualified_name=impl_sym.qualified_name,
                        callee_qualified_name=tgt_sym.qualified_name,
                        kind="overrides",
                        confidence=rel_conf,
                    )

    return sorted(
        candidates_map.values(),
        key=lambda c: (
            c.caller_path,
            c.caller_qualified_name or c.caller_symbol or "",
            c.callee_path,
            c.callee_qualified_name or c.callee_symbol or "",
            c.kind,
            c.ref_kind or "",
        ),
    )


def write_scip_json(scip_result: ScipIndexResult, out_path: str | Path) -> None:
    """Write decoded SCIP index structure to scip.json."""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(scip_result.to_dict(), f, indent=2)
