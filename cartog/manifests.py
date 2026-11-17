"""Compatibility shim: this module moved to :mod:`cartog.scan.manifests` in R6.

Import from ``cartog.scan.manifests`` in new code.
"""

from cartog.scan.manifests import (
    IGNORED_DIRS,
    parse_docker_compose,
    parse_dockerfile,
    parse_github_workflow,
    parse_manifests,
    parse_package_json,
    parse_pyproject_toml,
    parse_requirements_file,
)

__all__ = [
    "IGNORED_DIRS",
    "parse_docker_compose",
    "parse_dockerfile",
    "parse_github_workflow",
    "parse_manifests",
    "parse_package_json",
    "parse_pyproject_toml",
    "parse_requirements_file",
]
