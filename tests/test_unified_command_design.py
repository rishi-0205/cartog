"""U1: the unified-command design is complete and discoverable.

U1 is a design gate, so the deliverable is a document, not code. These tests
keep the document from drifting into a sketch: it must name the command, the
options, the exit codes, the output tree, and the migration path, and
``AGENTS.md`` must link to it (the R3 rule that every ``docs/dev`` document is
reachable from the root entry point).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN = REPO_ROOT / "docs" / "dev" / "UNIFIED_COMMAND.md"
AGENTS = REPO_ROOT / "AGENTS.md"

REQUIRED_SECTIONS = (
    "## 1. Command",
    "## 2. Options",
    "## 3. Exit codes",
    "## 4. Output tree",
    "## 5. Migration",
)

REQUIRED_STAGE_COMMANDS = (
    "cartog parse",
    "cartog scip",
    "cartog build",
    "cartog map",
    "cartog check",
    "cartog flow",
    "cartog view",
    "cartog digest",
    "cartog query",
    "cartog doctor",
)

REQUIRED_OUTPUT_TOKENS = (
    "graph.json",
    "view/map.html",
    "diagrams/",
    "digest.md",
    "check.json",
    "meta.json",
    "logs/",
    "latest",
    "CARTOG_HOME",
)


def test_design_doc_has_options_and_exit_codes():
    """The design must be complete before implementation starts."""
    assert DESIGN.is_file(), f"missing design document: {DESIGN.relative_to(REPO_ROOT)}"
    text = DESIGN.read_text(encoding="utf-8")

    missing_sections = [section for section in REQUIRED_SECTIONS if section not in text]
    assert not missing_sections, f"design is missing section(s): {missing_sections}"

    missing_commands = [cmd for cmd in REQUIRED_STAGE_COMMANDS if cmd not in text]
    assert not missing_commands, f"design does not keep stage command(s): {missing_commands}"

    missing_tokens = [token for token in REQUIRED_OUTPUT_TOKENS if token not in text]
    assert not missing_tokens, f"design does not describe output token(s): {missing_tokens}"

    exit_section = text.split("## 3. Exit codes", 1)[1].split("## 4.", 1)[0]
    for code in ("`0`", "`1`", "`2`", "`3`"):
        assert code in exit_section, f"exit code {code} is not defined"

    assert "--out" in text, "design must define --out"
    assert "analyze" in text, "design must name the explicit unified entry point"
    assert "cartog analyze <path>" in text, "design must document `cartog analyze <path>`"
    assert (
        "The primary entry point is the bare positional form" not in text
    ), "design must not advertise an implicit `cartog <path>` form"
    assert "--keep N" in text, "design must define --keep N"
    assert "default `1`" in text, "design must default --keep to 1 (no history kept)"


def test_design_doc_is_linked_from_agents():
    """AGENTS.md must link every docs/dev document, including this one."""
    text = AGENTS.read_text(encoding="utf-8")
    assert "docs/dev/UNIFIED_COMMAND.md" in text, (
        "AGENTS.md does not link to docs/dev/UNIFIED_COMMAND.md"
    )
