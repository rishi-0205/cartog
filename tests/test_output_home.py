"""U2: per-user output home, CARTOG_HOME override, and collision-resistant keys.

The unified command must never default to a directory inside the Cartog checkout
or the analyzed repository, and two checkouts with the same basename must not
share a project folder.
"""

from __future__ import annotations

from cartog.core import output


def test_output_home_per_platform(tmp_path):
    """Each platform resolves to its documented data directory."""
    win = output.default_data_root(
        platform_="win32", env={"LOCALAPPDATA": str(tmp_path / "Local")}, home=tmp_path
    )
    assert win == tmp_path / "Local" / "cartog"

    win_fallback = output.default_data_root(platform_="win32", env={}, home=tmp_path)
    assert win_fallback == tmp_path / "AppData" / "Local" / "cartog"

    mac = output.default_data_root(platform_="darwin", env={}, home=tmp_path)
    assert mac == tmp_path / "Library" / "Application Support" / "cartog"

    linux_xdg = output.default_data_root(
        platform_="linux", env={"XDG_DATA_HOME": str(tmp_path / "xdg")}, home=tmp_path
    )
    assert linux_xdg == tmp_path / "xdg" / "cartog"

    linux = output.default_data_root(platform_="linux", env={}, home=tmp_path)
    assert linux == tmp_path / ".local" / "share" / "cartog"


def test_cartog_home_override(tmp_path):
    """CARTOG_HOME replaces the platform root and keeps the project layout."""
    home = tmp_path / "home"
    env = {"CARTOG_HOME": str(home)}
    assert output.resolve_home(platform_="linux", env=env) == home

    repo = tmp_path / "repo"
    loc = output.resolve_run_location(
        repo,
        run_id="20260101T000000Z",
        platform_="linux",
        env=env,
        home=tmp_path,
    )
    project = home / "projects" / output.project_folder_name(repo, platform_="linux")
    assert loc.run_dir == project / "runs" / "20260101T000000Z"
    assert loc.latest_dir == project / "latest"
    assert loc.cache_dir == project / "cache"
    assert loc.project_dir == project
    assert loc.uses_runs is True

    direct = output.resolve_run_location(
        repo, out=tmp_path / "direct", run_id="20260101T000000Z", platform_="linux", env=env
    )
    assert direct.run_dir == (tmp_path / "direct").resolve()
    assert direct.latest_dir is None
    assert direct.project_dir is None
    assert direct.uses_runs is False


def test_project_folder_is_sanitized(tmp_path):
    """Unsafe characters, reserved names, length, and collisions are handled."""
    assert output.sanitize_project_name("my repo (v2)") == "my-repo-v2"
    assert output.sanitize_project_name("  spaced  ") == "spaced"
    assert output.sanitize_project_name("CON") == "_CON"
    assert output.sanitize_project_name("lpt9") == "_lpt9"
    assert output.sanitize_project_name("...") == "repo"
    assert output.sanitize_project_name("") == "repo"
    assert len(output.sanitize_project_name("a" * 80)) == 40

    one = output.project_folder_name(tmp_path / "one", platform_="linux")
    two = output.project_folder_name(tmp_path / "two", platform_="linux")
    assert one != two
    assert one == output.project_folder_name(tmp_path / "one", platform_="linux")
    assert one.startswith("one-") and len(one.split("-")[-1]) == 8

    assert (
        output.normalize_target_path("C:\\Repo\\Src", platform_="win32")
        == "c:/repo/src"
    )
    assert output.normalize_target_path("C:/Repo/Src", platform_="linux") == "C:/Repo/Src"
