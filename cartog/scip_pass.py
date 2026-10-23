"""SCIP indexer execution, decoding, occurrence extraction, and call graph resolution."""

from dataclasses import dataclass, field
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Optional

from cartog.langs.base import SymbolRecord
from cartog.model import SourceRange
from cartog.scip_pb2 import Index

logger = logging.getLogger("cartog")


@dataclass
class ScipOccurrence:
    """Decoded SCIP occurrence within a document."""
    symbol: str
    range: SourceRange
    is_definition: bool
    roles: int = 0
    syntax_kind: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
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
        return {
            "relative_path": self.relative_path,
            "language": self.language,
            "definitions": [d.to_dict() for d in self.definitions],
            "references": [r.to_dict() for r in self.references],
        }


@dataclass
class ScipIndexResult:
    """Aggregated SCIP indexing and decoding result."""
    ran: bool
    indexer: Optional[str] = None
    documents: list[ScipDocument] = field(default_factory=list)
    error: Optional[str] = None
    definitions_by_symbol: dict[str, tuple[str, SourceRange]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "meta": {
                "ran": self.ran,
                "indexer": self.indexer,
                "documents_count": len(self.documents),
                "error": self.error,
            },
            "documents": [d.to_dict() for d in self.documents],
        }


@dataclass
class CallEdgeCandidate:
    """Resolved call candidate from caller function to callee function."""
    caller_path: str
    caller_symbol: Optional[str]
    callee_path: str
    callee_symbol: str
    evidence: list[str] = field(default_factory=list)
    count: int = 1


def normalize_scip_range(raw_range: list[int]) -> SourceRange:
    """Convert SCIP 3-tuple or 4-tuple range into a standard SourceRange."""
    if len(raw_range) == 3:
        line, start_col, end_col = raw_range
        return SourceRange(start_line=line, start_col=start_col, end_line=line, end_col=end_col)
    elif len(raw_range) >= 4:
        return SourceRange(
            start_line=raw_range[0],
            start_col=raw_range[1],
            end_line=raw_range[2],
            end_col=raw_range[3],
        )
    return SourceRange(start_line=0, start_col=0, end_line=0, end_col=0)


def decode_scip_index(scip_path: str | Path) -> ScipIndexResult:
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

    for doc in index.documents:
        rel_path = doc.relative_path.replace("\\", "/")
        scip_doc = ScipDocument(relative_path=rel_path, language=doc.language)

        for occ in doc.occurrences:
            # Filter out local symbols (e.g. "local 1", "local 42")
            if occ.symbol.startswith("local "):
                continue

            rng = normalize_scip_range(list(occ.range))
            is_def = bool(occ.symbol_roles & 0x1)

            rec = ScipOccurrence(
                symbol=occ.symbol,
                range=rng,
                is_definition=is_def,
                roles=occ.symbol_roles,
                syntax_kind=str(occ.syntax_kind) if occ.syntax_kind else None,
            )

            if is_def:
                scip_doc.definitions.append(rec)
                if occ.symbol not in defs_by_symbol:
                    defs_by_symbol[occ.symbol] = (rel_path, rng)
            else:
                scip_doc.references.append(rec)

        docs.append(scip_doc)

    return ScipIndexResult(
        ran=True,
        documents=docs,
        definitions_by_symbol=defs_by_symbol,
    )


def run_scip_indexer(
    target_path: str | Path,
    out_dir: str | Path,
    language: str = "python",
    project_name: Optional[str] = None,
    timeout_sec: int = 120,
) -> ScipIndexResult:
    """Run external SCIP indexer with pre-checks, timeouts, and graceful error handling."""
    target_p = Path(target_path).resolve()
    out_p = Path(out_dir).resolve()

    indexer_cmd: list[str] = []
    indexer_name = "scip-python" if language == "python" else "scip-typescript"

    is_win = sys.platform.startswith("win")
    which_bin = shutil.which(indexer_name)
    if not which_bin:
        reason = f"Indexer '{indexer_name}' not found on PATH."
        logger.warning(reason)
        return ScipIndexResult(ran=False, indexer=indexer_name, error=reason)

    # Pre-check execution (ensure indexer runs cleanly without crash)
    try:
        check_res = subprocess.run(
            [indexer_name, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            shell=is_win,
        )
        if check_res.returncode != 0:
            reason = f"Indexer '{indexer_name}' failed pre-check (exit code {check_res.returncode}): {check_res.stderr.strip()[:100]}"
            logger.warning(reason)
            return ScipIndexResult(ran=False, indexer=indexer_name, error=reason)
    except Exception as e:
        reason = f"Indexer '{indexer_name}' pre-check raised exception: {e}"
        logger.warning(reason)
        return ScipIndexResult(ran=False, indexer=indexer_name, error=reason)

    # Root hash directory in out_dir/.cartog/scip/<hash>/
    path_hash = hashlib.sha1(target_p.as_posix().encode("utf-8")).hexdigest()[:12]
    scip_out_dir = out_p / ".cartog" / "scip" / path_hash
    scip_out_dir.mkdir(parents=True, exist_ok=True)
    scip_out_file = scip_out_dir / "index.scip"

    proj = project_name or target_p.name

    if language == "python":
        indexer_cmd = [indexer_name, "index", target_p.as_posix(), "--project-name", proj]
    else:
        indexer_cmd = [indexer_name, "index", "--infer-tsconfig"]

    logger.info(f"Running SCIP indexer: {' '.join(indexer_cmd)}")

    try:
        proc = subprocess.run(
            indexer_cmd,
            cwd=target_p,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            shell=is_win,
        )
        if proc.returncode != 0:
            reason = f"SCIP indexer exited with code {proc.returncode}: {proc.stderr.strip()[:200]}"
            logger.warning(reason)
            return ScipIndexResult(ran=False, indexer=indexer_name, error=reason)

        # Move generated index.scip into scip_out_file
        local_index = target_p / "index.scip"
        if local_index.is_file():
            shutil.move(local_index, scip_out_file)

        if not scip_out_file.is_file():
            reason = "SCIP indexer completed but output index.scip was not produced."
            logger.warning(reason)
            return ScipIndexResult(ran=False, indexer=indexer_name, error=reason)

    except subprocess.TimeoutExpired:
        reason = f"SCIP indexer timed out after {timeout_sec}s."
        logger.warning(reason)
        return ScipIndexResult(ran=False, indexer=indexer_name, error=reason)
    except Exception as e:
        reason = f"SCIP indexer execution error: {e}"
        logger.warning(reason)
        return ScipIndexResult(ran=False, indexer=indexer_name, error=reason)

    result = decode_scip_index(scip_out_file)
    result.indexer = indexer_name
    return result


def find_enclosing_symbol(
    range_target: SourceRange, symbols: list[SymbolRecord]
) -> Optional[SymbolRecord]:
    """Find innermost function, method, or class enclosing the given range."""
    best_match: Optional[SymbolRecord] = None
    best_span: Optional[int] = None

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


def link_calls(
    scip_result: ScipIndexResult,
    symbols_by_file: dict[str, list[SymbolRecord]],
) -> list[CallEdgeCandidate]:
    """Map reference occurrences to caller and callee functions, constructing CallEdgeCandidates."""
    candidates_map: dict[tuple[str, Optional[str], str, str], CallEdgeCandidate] = {}

    for doc in scip_result.documents:
        caller_path = doc.relative_path
        caller_symbols = symbols_by_file.get(caller_path, [])

        for ref in doc.references:
            if ref.symbol not in scip_result.definitions_by_symbol:
                continue

            callee_path, def_range = scip_result.definitions_by_symbol[ref.symbol]
            callee_symbols = symbols_by_file.get(callee_path, [])

            # Step 15: Find enclosing function of reference in caller file
            caller_sym = find_enclosing_symbol(ref.range, caller_symbols)
            caller_sym_name = caller_sym.name if caller_sym else None

            # Step 16: Find defining function of target symbol in callee file
            callee_sym = find_enclosing_symbol(def_range, callee_symbols)
            if not callee_sym:
                continue
            callee_sym_name = callee_sym.name

            # Skip self-call unless inside the same function (recursive call)
            if caller_path == callee_path and caller_sym_name == callee_sym_name:
                continue

            evidence_str = f"{caller_path}:{ref.range.start_line}"
            key = (caller_path, caller_sym_name, callee_path, callee_sym_name)

            if key not in candidates_map:
                candidates_map[key] = CallEdgeCandidate(
                    caller_path=caller_path,
                    caller_symbol=caller_sym_name,
                    callee_path=callee_path,
                    callee_symbol=callee_sym_name,
                    evidence=[evidence_str],
                    count=1,
                )
            else:
                c = candidates_map[key]
                c.count += 1
                if len(c.evidence) < 3 and evidence_str not in c.evidence:
                    c.evidence.append(evidence_str)

    # Sort deterministically
    return sorted(
        candidates_map.values(),
        key=lambda c: (c.caller_path, c.caller_symbol or "", c.callee_path, c.callee_symbol),
    )


def write_scip_json(scip_result: ScipIndexResult, out_path: str | Path) -> None:
    """Write decoded SCIP index structure to scip.json."""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(scip_result.to_dict(), f, indent=2)
