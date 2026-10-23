"""Manifest parsing for project configuration and build files.

Extracts entry points, dependencies, container services, and CI jobs from:
- pyproject.toml
- requirements*.txt
- Dockerfile, Dockerfile.*
- docker-compose*.yml, docker-compose*.yaml, compose.yml, compose.yaml
- .github/workflows/*.yml, .github/workflows/*.yaml
- package.json
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tomllib
from typing import Any, Optional

from cartog.model import ManifestFacts
from cartog.scan import _load_gitignore

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    ".cartog",
    "cartog-out",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
}


def _clean_dep_name_and_spec(raw: str) -> tuple[str, str]:
    """Parse a requirement string into (package_name, version_spec)."""
    # Strip environment markers like ; python_version >= '3.8'
    clean = raw.split(";", 1)[0].strip()
    # Strip extras like requests[security] >= 2.0
    match = re.match(r"^([a-zA-Z0-9_\-\.]+)(?:\[.*?\])?\s*(.*)$", clean)
    if match:
        name = match.group(1).strip()
        spec = match.group(2).strip()
        return name, spec or "*"
    return clean, "*"


def parse_pyproject_toml(file_path: Path, rel_path: str, facts: ManifestFacts) -> None:
    """Extract entrypoints and dependencies from pyproject.toml."""
    try:
        data = tomllib.loads(file_path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return

    # 1. Entrypoints / Scripts
    # [project.scripts]
    proj = data.get("project", {})
    if isinstance(proj, dict):
        scripts = proj.get("scripts", {})
        if isinstance(scripts, dict):
            for name, target in scripts.items():
                facts.entrypoints.append({
                    "name": name,
                    "target": str(target),
                    "file": rel_path,
                    "kind": "script",
                })

        gui_scripts = proj.get("gui-scripts", {})
        if isinstance(gui_scripts, dict):
            for name, target in gui_scripts.items():
                facts.entrypoints.append({
                    "name": name,
                    "target": str(target),
                    "file": rel_path,
                    "kind": "gui_script",
                })

        # Dependencies: [project.dependencies]
        deps = proj.get("dependencies", [])
        if isinstance(deps, list):
            for dep in deps:
                if isinstance(dep, str):
                    pkg_name, ver_spec = _clean_dep_name_and_spec(dep)
                    facts.dependencies.append({
                        "name": pkg_name,
                        "version_spec": ver_spec,
                        "file": rel_path,
                        "manager": "pip",
                    })

        # Optional dependencies: [project.optional-dependencies]
        opt_deps = proj.get("optional-dependencies", {})
        if isinstance(opt_deps, dict):
            for group, g_deps in opt_deps.items():
                if isinstance(g_deps, list):
                    for dep in g_deps:
                        if isinstance(dep, str):
                            pkg_name, ver_spec = _clean_dep_name_and_spec(dep)
                            facts.dependencies.append({
                                "name": pkg_name,
                                "version_spec": ver_spec,
                                "file": rel_path,
                                "manager": "pip",
                                "group": group,
                            })

    # [tool.poetry.scripts]
    poetry = data.get("tool", {}).get("poetry", {})
    if isinstance(poetry, dict):
        p_scripts = poetry.get("scripts", {})
        if isinstance(p_scripts, dict):
            for name, target in p_scripts.items():
                facts.entrypoints.append({
                    "name": name,
                    "target": str(target),
                    "file": rel_path,
                    "kind": "script",
                })

        p_deps = poetry.get("dependencies", {})
        if isinstance(p_deps, dict):
            for pkg, ver in p_deps.items():
                if pkg.lower() != "python":
                    facts.dependencies.append({
                        "name": pkg,
                        "version_spec": str(ver) if ver else "*",
                        "file": rel_path,
                        "manager": "poetry",
                    })

    # [dependency-groups]
    dep_groups = data.get("dependency-groups", {})
    if isinstance(dep_groups, dict):
        for group, g_deps in dep_groups.items():
            if isinstance(g_deps, list):
                for dep in g_deps:
                    if isinstance(dep, str):
                        pkg_name, ver_spec = _clean_dep_name_and_spec(dep)
                        facts.dependencies.append({
                            "name": pkg_name,
                            "version_spec": ver_spec,
                            "file": rel_path,
                            "manager": "pip",
                            "group": group,
                        })


def parse_requirements_file(file_path: Path, rel_path: str, facts: ManifestFacts) -> None:
    """Extract dependencies from requirements*.txt file."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Skip pip flags
        if line.startswith("-") or line.startswith("--"):
            continue
        if " #" in line:
            line = line.split(" #", 1)[0].strip()

        pkg_name, ver_spec = _clean_dep_name_and_spec(line)
        if pkg_name:
            facts.dependencies.append({
                "name": pkg_name,
                "version_spec": ver_spec,
                "file": rel_path,
                "manager": "pip",
            })


def parse_package_json(file_path: Path, rel_path: str, facts: ManifestFacts) -> None:
    """Extract entrypoints and dependencies from package.json."""
    try:
        data = json.loads(file_path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return

    scripts = data.get("scripts", {})
    if isinstance(scripts, dict):
        for name, cmd in scripts.items():
            facts.entrypoints.append({
                "name": f"npm run {name}",
                "target": str(cmd),
                "file": rel_path,
                "kind": "npm_script",
            })

    for dep_key, manager_type in [("dependencies", "npm"), ("devDependencies", "npm-dev")]:
        deps = data.get(dep_key, {})
        if isinstance(deps, dict):
            for pkg, ver in deps.items():
                facts.dependencies.append({
                    "name": pkg,
                    "version_spec": str(ver),
                    "file": rel_path,
                    "manager": manager_type,
                })


def parse_dockerfile(file_path: Path, rel_path: str, facts: ManifestFacts) -> None:
    """Extract container service information from a Dockerfile."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return

    base_images = []
    ports = []
    cmd = None

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        m_from = re.match(r"^FROM\s+([^\s]+)", stripped, re.IGNORECASE)
        if m_from:
            base_images.append(m_from.group(1))
            continue

        m_expose = re.match(r"^EXPOSE\s+(.+)", stripped, re.IGNORECASE)
        if m_expose:
            ports.extend(m_expose.group(1).split())
            continue

        m_cmd = re.match(r"^(?:CMD|ENTRYPOINT)\s+(.+)", stripped, re.IGNORECASE)
        if m_cmd and not cmd:
            cmd = m_cmd.group(1).strip()

    svc_name = f"docker:{rel_path}"
    facts.services.append({
        "name": svc_name,
        "image": base_images[0] if base_images else None,
        "ports": ports,
        "file": rel_path,
        "cmd": cmd,
    })


def parse_docker_compose(file_path: Path, rel_path: str, facts: ManifestFacts) -> None:
    """Extract container services from docker-compose.yml or compose.yml."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return

    lines = content.splitlines()
    in_services = False
    services_indent = 0
    current_svc: Optional[str] = None
    current_data: dict[str, Any] = {}
    svc_indent = 0

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())

        if not in_services:
            if re.match(r"^services\s*:", stripped):
                in_services = True
                services_indent = indent
            continue

        if indent <= services_indent:
            break

        match_svc = re.match(r"^([a-zA-Z0-9_\-]+)\s*:", stripped)
        if match_svc and (svc_indent == 0 or indent == svc_indent):
            if current_svc:
                facts.services.append({
                    "name": current_svc,
                    "file": rel_path,
                    **current_data,
                })
            current_svc = match_svc.group(1)
            current_data = {"image": None, "ports": [], "build": None}
            svc_indent = indent
            continue

        if current_svc and indent > svc_indent:
            m_img = re.match(r"^image\s*:\s*['\"]?(.*?)['\"]?$", stripped)
            if m_img:
                current_data["image"] = m_img.group(1).strip()
                continue
            m_bld = re.match(r"^build\s*:\s*['\"]?(.*?)['\"]?$", stripped)
            if m_bld:
                current_data["build"] = m_bld.group(1).strip()
                continue
            m_port = re.match(r"^-\s*['\"]?([0-9:\-\s/]+)['\"]?$", stripped)
            if m_port:
                current_data["ports"].append(m_port.group(1).strip())
                continue

    if current_svc:
        facts.services.append({
            "name": current_svc,
            "file": rel_path,
            **current_data,
        })


def parse_github_workflow(file_path: Path, rel_path: str, facts: ManifestFacts) -> None:
    """Extract CI workflow and job definitions from GitHub Actions workflow files."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return

    lines = content.splitlines()
    workflow_name = file_path.stem
    in_jobs = False
    jobs_indent = 0
    current_job_id: Optional[str] = None
    current_job_name: Optional[str] = None
    job_indent = 0

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())

        if not in_jobs:
            m_wf_name = re.match(r"^name\s*:\s*['\"]?(.*?)['\"]?$", stripped)
            if m_wf_name and indent == 0:
                workflow_name = m_wf_name.group(1).strip() or workflow_name
            elif re.match(r"^jobs\s*:", stripped):
                in_jobs = True
                jobs_indent = indent
            continue

        if indent <= jobs_indent:
            break

        match_job = re.match(r"^([a-zA-Z0-9_\-]+)\s*:", stripped)
        if match_job and (job_indent == 0 or indent == job_indent):
            if current_job_id:
                disp_name = (
                    current_job_name
                    if current_job_name and not current_job_name.startswith("${{")
                    else current_job_id
                )
                facts.ci_jobs.append({
                    "name": disp_name,
                    "workflow": workflow_name,
                    "job_id": current_job_id,
                    "file": rel_path,
                })
            current_job_id = match_job.group(1)
            current_job_name = None
            job_indent = indent
            continue

        if current_job_id and indent > job_indent:
            m_name = re.match(r"^name\s*:\s*['\"]?(.*?)['\"]?$", stripped)
            if m_name and not current_job_name:
                current_job_name = m_name.group(1).strip()

    if current_job_id:
        disp_name = (
            current_job_name
            if current_job_name and not current_job_name.startswith("${{")
            else current_job_id
        )
        facts.ci_jobs.append({
            "name": disp_name,
            "workflow": workflow_name,
            "job_id": current_job_id,
            "file": rel_path,
        })


def parse_manifests(target_dir: str | Path) -> ManifestFacts:
    """Discover and parse all manifest files in the target directory."""
    root_path = Path(target_dir).resolve()
    if not root_path.exists() or not root_path.is_dir():
        return ManifestFacts()

    facts = ManifestFacts()
    gitignore_spec = _load_gitignore(root_path)

    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
        current_dir = Path(dirpath)

        # Filter out ignored directories
        pruned_dirs = []
        for d in dirnames:
            if d in IGNORED_DIRS or (d.startswith(".") and d != ".github"):
                continue
            child_rel = (current_dir / d).relative_to(root_path).as_posix()
            if gitignore_spec and (gitignore_spec.match_file(child_rel) or gitignore_spec.match_file(child_rel + "/")):
                continue
            pruned_dirs.append(d)
        dirnames[:] = pruned_dirs

        try:
            rel_dir = current_dir.relative_to(root_path)
            rel_dir_posix = rel_dir.as_posix()
        except ValueError:
            continue

        for fname in filenames:
            file_path = current_dir / fname
            rel_file = (
                f"{rel_dir_posix}/{fname}"
                if rel_dir_posix != "."
                else fname
            )

            if gitignore_spec and gitignore_spec.match_file(rel_file):
                continue

            # 1. pyproject.toml
            if fname == "pyproject.toml":
                parse_pyproject_toml(file_path, rel_file, facts)

            # 2. package.json
            elif fname == "package.json":
                parse_package_json(file_path, rel_file, facts)

            # 3. requirements*.txt
            elif fname.startswith("requirements") and fname.endswith(".txt"):
                parse_requirements_file(file_path, rel_file, facts)

            # 4. Dockerfile
            elif fname == "Dockerfile" or fname.startswith("Dockerfile."):
                parse_dockerfile(file_path, rel_file, facts)

            # 5. docker-compose
            elif fname in (
                "docker-compose.yml",
                "docker-compose.yaml",
                "compose.yml",
                "compose.yaml",
            ):
                parse_docker_compose(file_path, rel_file, facts)

            # 6. GitHub Actions Workflows
            elif (
                ".github/workflows" in rel_file
                and (fname.endswith(".yml") or fname.endswith(".yaml"))
            ):
                parse_github_workflow(file_path, rel_file, facts)

    # Deduplicate dependencies by (name.lower(), file, group)
    seen_deps: set[tuple[str, str, Optional[str]]] = set()
    unique_deps = []
    for dep in facts.dependencies:
        key = (dep["name"].lower(), dep.get("file", ""), dep.get("group"))
        if key not in seen_deps:
            seen_deps.add(key)
            unique_deps.append(dep)
    facts.dependencies = unique_deps

    # Sort deterministically
    facts.entrypoints.sort(key=lambda ep: (ep.get("file", ""), ep["name"]))
    facts.dependencies.sort(key=lambda d: (d.get("file", ""), d["name"]))
    facts.services.sort(key=lambda s: (s.get("file", ""), s["name"]))
    facts.ci_jobs.sort(key=lambda j: (j.get("file", ""), j["name"]))

    return facts
