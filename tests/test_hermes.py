from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from bookmem import hermes, paths


@pytest.fixture(autouse=True)
def _clean_paths_state(monkeypatch):
    monkeypatch.delenv("BOOKMEM_HOME", raising=False)
    paths.set_home_override(None)
    yield
    paths.set_home_override(None)


# --- hermes init ---------------------------------------------------------

def test_hermes_init_dry_run_writes_nothing(monkeypatch, tmp_path):
    home = tmp_path / "bm"
    monkeypatch.setenv("BOOKMEM_HOME", str(home))
    report = hermes.hermes_init(dry_run=True)
    assert report["status"] == "planned"
    assert report["created_dirs"], "dry-run should still report planned directories"
    assert not (home / "data").exists()
    assert not (home / "config" / "bmdc.yaml").exists()


def test_hermes_init_creates_runtime_layout(monkeypatch, tmp_path):
    home = tmp_path / "bm"
    monkeypatch.setenv("BOOKMEM_HOME", str(home))
    report = hermes.hermes_init()
    assert report["status"] == "ok"
    for rel in (
        "config",
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
    ):
        assert (home / rel).is_dir(), f"missing runtime directory: {rel}"
    assert (home / "config" / "bmdc.yaml").exists()
    assert (home / "config" / "profiles" / "hermes.yaml").exists()


def test_hermes_init_is_idempotent(monkeypatch, tmp_path):
    home = tmp_path / "bm"
    monkeypatch.setenv("BOOKMEM_HOME", str(home))
    hermes.hermes_init()
    report = hermes.hermes_init()
    assert report["created_dirs"] == []
    assert report["copied_config_files"] == []


def test_hermes_init_does_not_overwrite_config_without_force(monkeypatch, tmp_path):
    home = tmp_path / "bm"
    monkeypatch.setenv("BOOKMEM_HOME", str(home))
    hermes.hermes_init()
    taxonomy = home / "config" / "bmdc.yaml"
    marker = "# user edited\n"
    taxonomy.write_text(marker, encoding="utf-8")

    hermes.hermes_init()  # no force
    assert taxonomy.read_text(encoding="utf-8") == marker

    hermes.hermes_init(force=True)  # force overwrites
    assert taxonomy.read_text(encoding="utf-8") != marker


def test_hermes_init_targets_bookmem_home(monkeypatch, tmp_path):
    home = tmp_path / "elsewhere" / "bm"
    monkeypatch.setenv("BOOKMEM_HOME", str(home))
    report = hermes.hermes_init()
    assert report["home"] == str(home)
    assert home.is_dir()


# --- hermes profile resolution ------------------------------------------

def test_hermes_profile_seeds_bookmem_home(monkeypatch):
    from bookmem.profiles import profile_environment

    monkeypatch.delenv("BOOKMEM_HOME", raising=False)
    with profile_environment("hermes"):
        assert "bookmem" in (os.environ.get("BOOKMEM_HOME") or "")


def test_explicit_bookmem_home_beats_hermes_profile(monkeypatch, tmp_path):
    from bookmem.profiles import profile_environment

    monkeypatch.setenv("BOOKMEM_HOME", str(tmp_path / "explicit"))
    with profile_environment("hermes"):
        assert os.environ["BOOKMEM_HOME"] == str(tmp_path / "explicit")


# --- install-wrapper -----------------------------------------------------

def _fake_hermes_venv(monkeypatch, tmp_path, console_script=True):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    venv_bin = tmp_path / ".hermes" / "hermes-agent" / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "python").write_text("", encoding="utf-8")
    if console_script:
        (venv_bin / "bookmem").write_text("", encoding="utf-8")
    return tmp_path / ".hermes" / "bin" / "bookmem"


def test_install_wrapper_dry_run(monkeypatch, tmp_path):
    wrapper = _fake_hermes_venv(monkeypatch, tmp_path)
    report = hermes.install_wrapper(dry_run=True)
    assert report["status"] == "planned"
    assert not wrapper.exists()


def test_install_wrapper_creates_executable(monkeypatch, tmp_path):
    wrapper = _fake_hermes_venv(monkeypatch, tmp_path)
    report = hermes.install_wrapper()
    assert report["status"] == "ok"
    assert wrapper.is_file()
    assert os.access(wrapper, os.X_OK)
    script = wrapper.read_text(encoding="utf-8")
    assert "BOOKMEM_HOME" in script
    assert "--profile hermes" in script


def test_install_wrapper_uses_venv_console_script(monkeypatch, tmp_path):
    _fake_hermes_venv(monkeypatch, tmp_path, console_script=True)
    report = hermes.install_wrapper()
    assert report["target_kind"] == "console-script"
    assert "hermes-agent/venv/bin/bookmem" in report["script"]


def test_install_wrapper_falls_back_to_python_module(monkeypatch, tmp_path):
    _fake_hermes_venv(monkeypatch, tmp_path, console_script=False)
    report = hermes.install_wrapper()
    assert report["target_kind"] == "python-module"
    assert "-m bookmem.cli" in report["script"]


def test_install_wrapper_does_not_overwrite_without_force(monkeypatch, tmp_path):
    wrapper = _fake_hermes_venv(monkeypatch, tmp_path)
    hermes.install_wrapper()
    wrapper.write_text("CUSTOM\n", encoding="utf-8")

    report = hermes.install_wrapper()
    assert report["status"] == "skipped"
    assert wrapper.read_text(encoding="utf-8") == "CUSTOM\n"

    hermes.install_wrapper(force=True)
    assert wrapper.read_text(encoding="utf-8") != "CUSTOM\n"


def test_install_wrapper_errors_without_hermes_venv(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    report = hermes.install_wrapper()
    assert report["status"] == "error"


def test_install_instructions_mention_pip_into_hermes_venv():
    info = hermes.install_instructions()
    assert "python -m pip install" in info["install"]
    assert "hermes-agent/venv" in info["install"]
    assert "-e ." in info["editable_install"]


# --- passivity -----------------------------------------------------------

def _heavy_modules_loaded_by(import_and_call: str, home: str) -> str:
    """Run code in a fresh interpreter and report any embedding/HF deps loaded.

    Passive status commands must not load sentence-transformers, pull in torch
    or contact Hugging Face. (Importing the lightweight ``lancedb`` module is
    allowed; passive commands simply never *connect* to a database.)
    """
    code = (
        "import sys\n"
        f"{import_and_call}\n"
        "heavy = ('sentence_transformers', 'torch', 'huggingface_hub')\n"
        "bad = [m for m in heavy if m in sys.modules]\n"
        "print('LOADED:' + ','.join(bad) if bad else 'PASSIVE')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={**os.environ, "BOOKMEM_HOME": home},
    )
    return (result.stdout + result.stderr).strip()


def test_hermes_status_is_passive(tmp_path):
    out = _heavy_modules_loaded_by(
        "from bookmem.hermes import hermes_status\nhermes_status()",
        str(tmp_path),
    )
    assert out == "PASSIVE", out


def test_setup_status_is_passive(tmp_path):
    out = _heavy_modules_loaded_by(
        "from bookmem.setup_wizard import setup_status\nsetup_status()",
        str(tmp_path),
    )
    assert out == "PASSIVE", out


# --- book discovery skips support markdown -------------------------------

def test_support_markdown_not_discovered_as_books(tmp_path):
    from bookmem.book_files import discover_book_markdown_files

    for support in ("README.md", "CHANGELOG.md", "LICENSE.md", "CONTRIBUTING.md"):
        (tmp_path / support).write_text(f"# {support}\n", encoding="utf-8")
    book = tmp_path / "Real Book - Author - 9780306406157.md"
    book.write_text("---\ntitle: Real Book\n---\n\n# Real Book\n", encoding="utf-8")

    found = {path.name for path in discover_book_markdown_files(tmp_path)}
    assert book.name in found
    assert "README.md" not in found
    assert "CHANGELOG.md" not in found
    assert "CONTRIBUTING.md" not in found
