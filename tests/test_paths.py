from __future__ import annotations

from pathlib import Path

import pytest

from bookmem import paths


@pytest.fixture(autouse=True)
def _clean_paths_state(monkeypatch):
    """Each test starts with no --home override and no BOOKMEM_HOME."""
    monkeypatch.delenv("BOOKMEM_HOME", raising=False)
    paths.set_home_override(None)
    yield
    paths.set_home_override(None)


def test_standalone_home_is_cwd(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "running_in_hermes_venv", lambda: False)
    monkeypatch.chdir(tmp_path)
    assert paths.get_bookmem_home() == tmp_path
    assert paths.home_is_explicit() is False
    assert paths.home_source() == "current-directory"


def test_bookmem_home_env_override(monkeypatch, tmp_path):
    target = tmp_path / "runtime"
    monkeypatch.setenv("BOOKMEM_HOME", str(target))
    assert paths.get_bookmem_home() == target
    assert paths.home_is_explicit() is True
    assert paths.home_source() == "environment"


def test_home_option_overrides_env(monkeypatch, tmp_path):
    monkeypatch.setenv("BOOKMEM_HOME", str(tmp_path / "from-env"))
    paths.set_home_override(tmp_path / "from-cli")
    assert paths.get_bookmem_home() == tmp_path / "from-cli"
    assert paths.home_source() == "cli-option"


def test_bookmem_home_expands_user(monkeypatch):
    monkeypatch.setenv("BOOKMEM_HOME", "~/somewhere-bookmem")
    assert paths.get_bookmem_home() == Path.home() / "somewhere-bookmem"


def test_activate_home_standalone_is_noop(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "running_in_hermes_venv", lambda: False)
    monkeypatch.chdir(tmp_path)
    before = Path.cwd()
    result = paths.activate_home()
    assert result == before
    assert Path.cwd() == before


def test_activate_home_explicit_chdirs_into_root(monkeypatch, tmp_path):
    target = tmp_path / "explicit-home"
    monkeypatch.setenv("BOOKMEM_HOME", str(target))
    monkeypatch.chdir(tmp_path)
    result = paths.activate_home()
    assert result == target.resolve()
    assert Path.cwd() == target.resolve()
    assert target.is_dir()


def test_directory_accessors_root_at_home(monkeypatch, tmp_path):
    monkeypatch.setenv("BOOKMEM_HOME", str(tmp_path))
    assert paths.books_dir() == tmp_path / "data" / "books"
    assert paths.raw_books_dir() == tmp_path / "data" / "raw-books"
    assert paths.lancedb_dir() == tmp_path / "data" / "lancedb"
    assert paths.config_dir() == tmp_path / "config"
    assert paths.exports_dir() == tmp_path / "exports"
    assert paths.backups_dir() == tmp_path / "backups"
    assert paths.logs_dir() == tmp_path / "logs"
    assert paths.audit_dir() == tmp_path / "data" / "audit"


def test_settings_follow_bookmem_home(monkeypatch, tmp_path):
    from bookmem.config import get_settings

    monkeypatch.setenv("BOOKMEM_HOME", str(tmp_path))
    settings = get_settings()
    assert settings.books_dir == tmp_path / "data" / "books"
    assert settings.db_dir == tmp_path / "data" / "lancedb"
    assert settings.taxonomy_path == tmp_path / "config" / "bmdc.yaml"


def test_explicit_bookmem_path_env_still_overrides(monkeypatch, tmp_path):
    from bookmem.config import get_settings

    monkeypatch.setenv("BOOKMEM_HOME", str(tmp_path))
    monkeypatch.setenv("BOOKMEM_BOOKS_DIR", str(tmp_path / "custom-books"))
    settings = get_settings()
    assert settings.books_dir == tmp_path / "custom-books"


def test_citation_config_follows_bookmem_home(monkeypatch, tmp_path):
    """Citation/reference config resolves under the runtime home, not the
    installed package directory (which differs for non-editable installs)."""
    from bookmem.citation_exports import (
        _export_format_config_dir,
        _export_format_config_path,
        _style_config_dir,
        _style_config_path,
    )

    monkeypatch.setenv("BOOKMEM_HOME", str(tmp_path))
    assert _style_config_path() == tmp_path / "config" / "citation_styles.yaml"
    assert _style_config_dir() == tmp_path / "config" / "citation_styles.d"
    assert _export_format_config_path() == tmp_path / "config" / "reference_export_formats.yaml"
    assert _export_format_config_dir() == tmp_path / "config" / "reference_export_formats.d"
