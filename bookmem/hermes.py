"""Hermes agent integration for BookMem.

Backs the ``bookmem hermes`` command group. The BookMem Python package is
installed into the Hermes agent virtualenv (``~/.hermes/hermes-agent/venv``),
while runtime data and config live separately under ``~/.hermes/bookmem`` so
nothing is written inside the venv and no repo checkout needs to be the
current working directory.

All functions here are filesystem-only: they never load embedding models,
initialise LanceDB or contact Hugging Face, so ``hermes status`` stays passive.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from shutil import copy2
from typing import Any

from . import paths

HERMES_INTEGRATION_VERSION = "0.1.0"


def _bundled_config_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def hermes_init(dry_run: bool = False, force: bool = False) -> dict[str, Any]:
    """Create the Hermes runtime home and seed it with default config.

    Idempotent: existing directories and config files are left untouched unless
    ``force`` is set. With ``dry_run`` nothing is written; the report describes
    what would happen.
    """
    home = paths.get_bookmem_home().expanduser()

    created_dirs: list[str] = []
    existing_dirs: list[str] = []
    copied_files: list[str] = []
    skipped_files: list[str] = []
    warnings: list[str] = []

    for target in [home] + [home / rel for rel in paths.RUNTIME_SUBDIRS]:
        if target.is_dir():
            existing_dirs.append(str(target))
        else:
            created_dirs.append(str(target))
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)

    config_target = home / "config"
    bundled = paths.bundled_config_dir()
    if bundled is None:
        warnings.append(
            "Bundled default config not found. Copy the repository's config/ "
            f"directory into {config_target} manually."
        )
    else:
        for src in _bundled_config_files(bundled):
            dest = config_target / src.relative_to(bundled)
            if dest.exists() and not force:
                skipped_files.append(str(dest))
                continue
            copied_files.append(str(dest))
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                copy2(src, dest)

    hermes_profile = config_target / "profiles" / "hermes.yaml"
    hermes_profile_present = hermes_profile.exists() or str(hermes_profile) in copied_files
    if not hermes_profile_present:
        warnings.append(
            "config/profiles/hermes.yaml was not created; the bundled config "
            "may be missing it. `bookmem --profile hermes` still works from the "
            "bundled profile."
        )

    return {
        "schema_version": 1,
        "hermes_integration_version": HERMES_INTEGRATION_VERSION,
        "home": str(home),
        "dry_run": dry_run,
        "force": force,
        "created_dirs": created_dirs,
        "existing_dirs": existing_dirs,
        "copied_config_files": copied_files,
        "skipped_config_files": skipped_files,
        "hermes_profile": str(hermes_profile),
        "hermes_profile_present": hermes_profile_present,
        "warnings": warnings,
        "status": "planned" if dry_run else "ok",
    }


def hermes_status() -> dict[str, Any]:
    """Report Hermes integration health. Passive: no embeddings, no LanceDB."""
    home = paths.get_bookmem_home().expanduser()
    venv = paths.hermes_venv_dir()
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    home_exists = home.is_dir()
    add("home_exists", home_exists, str(home))

    missing_dirs = [rel for rel in paths.RUNTIME_SUBDIRS if not (home / rel).is_dir()]
    add(
        "runtime_dirs",
        not missing_dirs,
        "all present" if not missing_dirs else f"missing: {', '.join(missing_dirs)}",
    )

    taxonomy = home / "config" / "bmdc.yaml"
    add("config_seeded", taxonomy.exists(), str(taxonomy))

    profile_detail = ""
    profile_ok = False
    try:
        from .profiles import get_profile

        profile = get_profile("hermes")
        profile_ok = True
        profile_detail = f"loaded (home_dir={profile.home_dir})"
    except Exception as exc:  # noqa: BLE001 - report any load failure
        profile_detail = f"failed to load: {exc}"
    add("hermes_profile_loads", profile_ok, profile_detail)

    for label, directory in (
        ("raw_books_dir", home / "data" / "raw-books"),
        ("books_dir", home / "data" / "books"),
        ("lancedb_dir", home / "data" / "lancedb"),
    ):
        add(label, directory.is_dir(), str(directory))

    writable = home_exists and os.access(home, os.W_OK)
    add("home_writable", writable, "writable" if writable else "not writable")

    try:
        venv_resolved = venv.resolve()
        home_inside_venv = home == venv_resolved or venv_resolved in home.resolve().parents
    except OSError:
        home_inside_venv = False
    add(
        "home_outside_venv",
        not home_inside_venv,
        "runtime home is inside the Hermes venv" if home_inside_venv else "runtime home is separate from the venv",
    )

    return {
        "schema_version": 1,
        "hermes_integration_version": HERMES_INTEGRATION_VERSION,
        "passive": True,
        "home": str(home),
        "home_source": paths.home_source(),
        "bookmem_home_env": os.getenv("BOOKMEM_HOME"),
        "running_in_hermes_venv": paths.running_in_hermes_venv(),
        "interpreter": sys.executable,
        "hermes_venv": str(venv),
        "checks": checks,
        "ok": all(check["ok"] for check in checks),
        "status": "ok" if all(check["ok"] for check in checks) else "warn",
    }


def _wrapper_script(exec_line: str) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "\n"
        "# Generated by `bookmem hermes install-wrapper`.\n"
        'export BOOKMEM_HOME="${BOOKMEM_HOME:-$HOME/.hermes/bookmem}"\n'
        f"{exec_line}\n"
    )


def install_wrapper(dry_run: bool = False, force: bool = False) -> dict[str, Any]:
    """Create ``~/.hermes/bin/bookmem``, a wrapper that runs BookMem from the
    Hermes venv with ``BOOKMEM_HOME`` set and the ``hermes`` profile selected.
    """
    bin_dir = paths.hermes_bin_dir()
    wrapper = bin_dir / "bookmem"
    venv_bin = paths.hermes_venv_dir() / "bin"
    console_script = venv_bin / "bookmem"
    venv_python = venv_bin / "python"

    if console_script.exists():
        target_kind = "console-script"
        exec_line = 'exec "$HOME/.hermes/hermes-agent/venv/bin/bookmem" --profile hermes "$@"'
    elif venv_python.exists():
        target_kind = "python-module"
        exec_line = (
            'exec "$HOME/.hermes/hermes-agent/venv/bin/python" -m bookmem.cli '
            '--profile hermes "$@"'
        )
    else:
        return {
            "schema_version": 1,
            "status": "error",
            "wrapper": str(wrapper),
            "dry_run": dry_run,
            "message": (
                f"Hermes agent venv not found at {paths.hermes_venv_dir()}. "
                "Install BookMem into it first with: "
                "$HOME/.hermes/hermes-agent/venv/bin/python -m pip install -U ."
            ),
        }

    script = _wrapper_script(exec_line)

    if wrapper.exists() and not force:
        return {
            "schema_version": 1,
            "status": "skipped",
            "wrapper": str(wrapper),
            "target_kind": target_kind,
            "dry_run": dry_run,
            "script": script,
            "message": "Wrapper already exists; pass --force to overwrite.",
        }

    if dry_run:
        return {
            "schema_version": 1,
            "status": "planned",
            "wrapper": str(wrapper),
            "target_kind": target_kind,
            "dry_run": True,
            "script": script,
            "message": f"Would write {wrapper}",
        }

    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper.write_text(script, encoding="utf-8")
    wrapper.chmod(0o755)

    return {
        "schema_version": 1,
        "status": "ok",
        "wrapper": str(wrapper),
        "target_kind": target_kind,
        "dry_run": False,
        "script": script,
        "message": f"Installed wrapper at {wrapper}",
    }


def install_instructions() -> dict[str, Any]:
    """Return the canonical Hermes install commands (for `hermes install-help`)."""
    return {
        "schema_version": 1,
        "package_target": str(paths.hermes_venv_dir()),
        "runtime_home": str(paths.hermes_home()),
        "install": "$HOME/.hermes/hermes-agent/venv/bin/python -m pip install -U .",
        "editable_install": "$HOME/.hermes/hermes-agent/venv/bin/python -m pip install -U -e .",
        "post_install": [
            "$HOME/.hermes/hermes-agent/venv/bin/bookmem hermes init",
            "$HOME/.hermes/hermes-agent/venv/bin/bookmem hermes install-wrapper",
        ],
        "notes": [
            "Installs the BookMem package into the Hermes venv.",
            "Runtime data/config live under ~/.hermes/bookmem, not in the venv.",
            "BookMem does not create a separate virtualenv for Hermes mode.",
        ],
    }
