"""Global constants and configuration for Cartog."""

SCHEMA_VERSION = "1.0.0"

DEFAULT_OUT_DIR = "cartog-out"
DEFAULT_CACHE_DIR = ".cartog"
DEFAULT_MAX_FILE_SIZE_MB = 1.0
DEFAULT_MAX_FILE_SIZE_BYTES = int(DEFAULT_MAX_FILE_SIZE_MB * 1024 * 1024)
DEFAULT_MAX_FILE_SIZE = DEFAULT_MAX_FILE_SIZE_BYTES  # 1 MB alias

DEFAULT_IGNORED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    "build",
    "dist",
    "out",
    ".next",
    "coverage",
    ".tox",
    ".mypy_cache",
    ".cartog",
    "cartog-out",
}

DEFAULT_IGNORED_GLOBS = [
    "*.min.js",
    "package-lock.json",
    "poetry.lock",
    "yarn.lock",
    "pnpm-lock.yaml",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.map",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.ico",
    "*.svg",
    "*.woff",
    "*.woff2",
    "*.ttf",
    "*.eot",
]

SUPPORTED_LANGUAGES = ["python", "javascript", "typescript"]
