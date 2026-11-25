"""U3: the stable output tree, atomic writes, latest copy, and retention."""

from __future__ import annotations

import json
import os

from cartog import __version__
from cartog.core import output


def _location(tmp_path, run_id: str) -> output.RunLocation:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    return output.resolve_run_location(
        repo,
        run_id=run_id,
        platform_="linux",
        env={"CARTOG_HOME": str(home)},
        home=tmp_path,
    )


def _layout(tmp_path, run_id: str) -> output.RunLayout:
    return output.RunLayout(_location(tmp_path, run_id))


def _meta(run_id: str) -> dict:
    return output.build_meta(
        run_id=run_id,
        status="complete",
        project={"name": "repo", "hash": "1234abcd", "path": "/tmp/repo"},
        target={"path": "/tmp/repo", "languages": ["python"]},
        options={"scip": False, "check": True, "strict": False, "flow": None},
        counts={"files": 1, "nodes": 2, "edges": 1},
        tools={"cartog": __version__, "scip_python": None, "mmdc": None},
        started_at="2026-11-18T10:00:00+00:00",
        finished_at="2026-11-18T10:00:01+00:00",
        cartog_version=__version__,
        timings={"total_ms": 12.5},
    )


def test_output_layout_paths(tmp_path):
    """One finalized run produces the documented tree."""
    layout = _layout(tmp_path, "20261118T100000Z")
    layout.write_text("graph.json", "{}")
    layout.write_text("view/map.html", "<html></html>")
    layout.write_text("diagrams/overview.mmd", "flowchart TD")
    layout.write_text("diagrams/folder_pkg.mmd", "flowchart TD")
    layout.write_text("digest.md", "# Digest")
    layout.write_json("check.json", {"status": "pass"})
    layout.write_json("meta.json", _meta(layout.location.run_id))
    layout.write_text("logs/parse.log", "parsed")
    layout.write_text("stage/parse.json", "{}")
    layout.finalize(keep=1)

    expected = (
        ".complete",
        "graph.json",
        "view/map.html",
        "diagrams/overview.mmd",
        "diagrams/folder_pkg.mmd",
        "digest.md",
        "check.json",
        "meta.json",
        "logs/parse.log",
        "stage/parse.json",
    )
    for rel in expected:
        assert (layout.run_dir / rel).is_file(), f"missing {rel}"

    assert layout.location.latest_dir is not None
    assert (layout.location.latest_dir / "graph.json").is_file()
    meta = json.loads((layout.run_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["schema_version"] == "2.1.0"
    assert meta["cartog_version"] == __version__
    assert meta["started_at"] and meta["finished_at"]
    assert meta["timings"]["total_ms"] == 12.5


def test_latest_is_a_copy_not_a_symlink(tmp_path):
    """latest is a real directory copy, and editing it does not touch the run."""
    first = _layout(tmp_path, "20261118T100000Z")
    first.write_text("graph.json", "one")
    first.finalize(keep=5)

    second = _layout(tmp_path, "20261118T100001Z")
    second.write_text("graph.json", "two")
    second.finalize(keep=5)

    latest = second.location.latest_dir
    assert latest is not None
    assert latest.is_dir()
    assert not latest.is_symlink()
    if os.name == "nt":
        assert not (latest.stat().st_file_attributes & 0x400)
    assert (latest / "graph.json").read_text(encoding="utf-8") == "two"
    assert not (latest / ".complete").is_symlink()

    (latest / "graph.json").write_text("edited", encoding="utf-8")
    assert (second.run_dir / "graph.json").read_text(encoding="utf-8") == "two"


def test_meta_json_has_versions_and_timings(tmp_path):
    """meta.json records schema/cartog versions, start/finish, and timings."""
    layout = _layout(tmp_path, "20261118T100002Z")
    meta = _meta(layout.location.run_id)
    layout.write_json("meta.json", meta, pretty=True)
    loaded = json.loads((layout.run_dir / "meta.json").read_text(encoding="utf-8"))
    assert loaded["schema_version"] == "2.1.0"
    assert loaded["cartog_version"] == __version__
    assert loaded["run_id"] == "20261118T100002Z"
    assert loaded["started_at"] <= loaded["finished_at"]
    assert "total_ms" in loaded["timings"]


def test_run_retention_keeps_n_complete_runs(tmp_path):
    """--keep N keeps the newest N complete runs and drops older ones."""
    layouts = [_layout(tmp_path, f"20261118T10000{i}Z") for i in range(1, 5)]
    for layout in layouts:
        layout.write_text("graph.json", "{}")
        layout.mark_complete()

    stale = _layout(tmp_path, "20261118T095959Z")
    stale.write_text("graph.json", "{}")

    newest = _layout(tmp_path, "20261118T100050Z")
    newest.write_text("graph.json", "{}")
    newest.mark_complete()

    newer_incomplete = _layout(tmp_path, "20261118T100060Z")
    newer_incomplete.write_text("graph.json", "{}")

    victims = newest.finalize(keep=2)
    runs_dir = newest.location.run_dir.parent
    remaining = sorted(p.name for p in runs_dir.iterdir() if p.is_dir())

    assert [p.name for p in victims] == [
        layouts[0].run_dir.name,
        layouts[1].run_dir.name,
        layouts[2].run_dir.name,
    ]
    assert remaining == [
        layouts[-1].run_dir.name,
        newest.run_dir.name,
        newer_incomplete.run_dir.name,
    ]
    assert not (stale.run_dir).exists(), "incomplete runs older than the kept window are removed"
    assert (newer_incomplete.run_dir).exists(), "incomplete runs newer than the kept window stay"
    assert (newest.location.latest_dir / "graph.json").is_file()
    assert newest.location.latest_dir.name == "latest"


def test_run_retention_default_drops_history(tmp_path):
    """The default keep=1 leaves only the run that just finished."""
    old = _layout(tmp_path, "20261118T100010Z")
    old.write_text("graph.json", "{}")
    old.finalize()

    new = _layout(tmp_path, "20261118T100011Z")
    new.write_text("graph.json", "{}")
    new.finalize()

    runs_dir = new.location.run_dir.parent
    remaining = sorted(p.name for p in runs_dir.iterdir() if p.is_dir())
    assert remaining == ["20261118T100011Z"]


def test_out_directory_is_never_pruned(tmp_path):
    """--out is caller-owned: no latest and no retention."""
    out_dir = tmp_path / "direct"
    loc = output.resolve_run_location(
        tmp_path, out=out_dir, run_id="20261118T100000Z", platform_="linux"
    )
    layout = output.RunLayout(loc)
    layout.write_text("graph.json", "{}")
    layout.finalize(keep=1)
    (out_dir / "keep-me").write_text("x", encoding="utf-8")

    assert loc.uses_runs is False
    assert loc.latest_dir is None
    assert layout.prune(1) == []
    assert (out_dir / "keep-me").exists()
    assert (out_dir / "graph.json").exists()


def test_incomplete_run_is_not_latest(tmp_path):
    """A run without .complete never becomes latest."""
    layout = _layout(tmp_path, "20261118T100000Z")
    layout.write_text("graph.json", "{}")
    assert layout.publish_latest() is None
    assert layout.location.latest_dir is not None
    assert not layout.location.latest_dir.exists()
