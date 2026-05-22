"""Central runtime path resolution for BookMem.

BookMem can run in three modes:

- **Standalone** — paths resolve relative to the current working directory,
  exactly as they did before this module existed. This is the fallback.
- **Profile** — a config profile (e.g. ``hermes``) supplies ``paths.home_dir``.
- **Hermes** — when installed into the Hermes agent virtualenv, the runtime
  root defaults to ``~/.hermes/bookmem`` so data never lands inside the venv.

The runtime root (``BOOKMEM_HOME``) is resolved with this precedence:

1. an explicit ``--home`` CLI option (see :func:`set_home_override`),
2. the ``BOOKMEM_HOME`` environment variable (also set by profiles),
3. Hermes auto-detection (interpreter running inside the Hermes venv),
4. the current working directory (standalone fallback).

:func:`activate_home` makes the resolved root the process working directory
so the project's existing relative paths (``data/...``, ``config/...``) keep
working without a sweeping rewrite. In standalone mode it is a no-op.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PATHS_VERSION = "0.1.0"

# Set by the CLI when --home is passed; highest-priority root.
_home_override: Path | None = None

# Runtime directories created by `bookmem hermes init` and `bookmem setup`.
RUNTIME_SUBDIRS: list[str] = [
    "config",
    "data",
    "data/raw-books",
    "data/books",
    "data/lancedb",
    "data/manifests",
    "data/summaries",
    "data/review",
    "data/graphs",
    "data/concepts",
    "data/claims",
    "data/passages",
    "data/queries",
    "data/briefs",
    "data/reading-lists",
    "data/jobs",
    "data/audit",
    "data/notes",
    "exports",
    "backups",
    "logs",
]


def set_home_override(path: str | os.PathLike[str] | None) -> None:
    """Record an explicit ``--home`` value. Pass ``None`` to clear it."""
    global _home_override
    _home_override = Path(path).expanduser() if path else None


def home_override() -> Path | None:
    """Return the explicit ``--home`` override, if one was set."""
    return _home_override


def hermes_root() -> Path:
    """The Hermes base directory, ``~/.hermes``."""
    return Path.home() / ".hermes"


def hermes_venv_dir() -> Path:
    """The Hermes agent virtualenv, ``~/.hermes/hermes-agent/venv``."""
    return hermes_root() / "hermes-agent" / "venv"


def hermes_home() -> Path:
    """The Hermes BookMem runtime root, ``~/.hermes/bookmem``."""
    return hermes_root() / "bookmem"


def hermes_bin_dir() -> Path:
    """Directory for the Hermes ``bookmem`` wrapper, ``~/.hermes/bin``."""
    return hermes_root() / "bin"


def running_in_hermes_venv() -> bool:
    """True when the active interpreter lives in the Hermes agent venv."""
    try:
        return Path(sys.prefix).resolve() == hermes_venv_dir().resolve()
    except OSError:
        return False


def package_dir() -> Path:
    """Directory of the installed ``bookmem`` package."""
    return Path(__file__).resolve().parent


def bundled_config_dir() -> Path | None:
    """Locate the default config shipped with BookMem.

    For a regular (non-editable) install the ``config/`` tree is packaged into
    the wheel at ``bookmem/_bundled_config``. For an editable or source install
    it is the repository's top-level ``config/`` directory. Returns ``None`` if
    neither is present.
    """
    pkg = package_dir()
    for candidate in (pkg / "_bundled_config", pkg.parent / "config"):
        if candidate.is_dir():
            return candidate
    return None


def home_source() -> str:
    """Describe which rule decided the runtime root (for diagnostics)."""
    if _home_override is not None:
        return "cli-option"
    if (os.getenv("BOOKMEM_HOME") or "").strip():
        return "environment"
    if running_in_hermes_venv():
        return "hermes-auto-detect"
    return "current-directory"


def home_is_explicit() -> bool:
    """True when the root is deliberately set (not the standalone fallback)."""
    return home_source() != "current-directory"


def get_bookmem_home() -> Path:
    """Resolve the BookMem runtime root using the documented precedence."""
    if _home_override is not None:
        return _home_override
    env = (os.getenv("BOOKMEM_HOME") or "").strip()
    if env:
        return Path(env).expanduser()
    if running_in_hermes_venv():
        return hermes_home()
    return Path.cwd()


def activate_home() -> Path:
    """Resolve the runtime root and make it the working directory.

    When the root is explicit (``--home``, ``BOOKMEM_HOME`` or Hermes
    detection) the directory is created if missing and becomes the process
    working directory, so relative paths throughout BookMem resolve under it.

    In standalone mode (no explicit root) this is a deliberate no-op and the
    current working directory is left untouched.
    """
    if not home_is_explicit():
        return Path.cwd()
    home = get_bookmem_home().expanduser()
    home.mkdir(parents=True, exist_ok=True)
    home = home.resolve()
    if Path.cwd().resolve() != home:
        os.chdir(home)
    return home


def resolve_path(*parts: str) -> Path:
    """Return an absolute path under the runtime root."""
    return get_bookmem_home().joinpath(*parts)


# --- Directory accessors -------------------------------------------------
# Each returns an absolute path rooted at the resolved BookMem home.

def data_dir() -> Path:
    return resolve_path("data")


def raw_books_dir() -> Path:
    return resolve_path("data", "raw-books")


def books_dir() -> Path:
    return resolve_path("data", "books")


def lancedb_dir() -> Path:
    return resolve_path("data", "lancedb")


def config_dir() -> Path:
    return resolve_path("config")


def exports_dir() -> Path:
    return resolve_path("exports")


def backups_dir() -> Path:
    return resolve_path("backups")


def logs_dir() -> Path:
    return resolve_path("logs")


def manifests_dir() -> Path:
    return resolve_path("data", "manifests")


def summaries_dir() -> Path:
    return resolve_path("data", "summaries")


def review_dir() -> Path:
    return resolve_path("data", "review")


def graphs_dir() -> Path:
    return resolve_path("data", "graphs")


def concepts_dir() -> Path:
    return resolve_path("data", "concepts")


def claims_dir() -> Path:
    return resolve_path("data", "claims")


def passages_dir() -> Path:
    return resolve_path("data", "passages")


def queries_dir() -> Path:
    return resolve_path("data", "queries")


def briefs_dir() -> Path:
    return resolve_path("data", "briefs")


def reading_lists_dir() -> Path:
    return resolve_path("data", "reading-lists")


def jobs_dir() -> Path:
    return resolve_path("data", "jobs")


def audit_dir() -> Path:
    return resolve_path("data", "audit")


def notes_dir() -> Path:
    return resolve_path("data", "notes")


def runtime_layout() -> dict[str, str]:
    """Return the resolved runtime directory layout (for diagnostics)."""
    return {
        "home": str(get_bookmem_home()),
        "home_source": home_source(),
        "config": str(config_dir()),
        "data": str(data_dir()),
        "raw_books": str(raw_books_dir()),
        "books": str(books_dir()),
        "lancedb": str(lancedb_dir()),
        "exports": str(exports_dir()),
        "backups": str(backups_dir()),
        "logs": str(logs_dir()),
    }
