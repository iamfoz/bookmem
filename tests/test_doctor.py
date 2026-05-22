from __future__ import annotations

from pathlib import Path

import yaml

from bookmem.doctor import check_config_files


def test_doctor_fix_restores_placeholder_config(tmp_path, monkeypatch):
    """`doctor --fix` must restore a missing/empty config file from the
    packaged defaults, not leave a useless comment-only placeholder."""
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    # Reproduce the old `doctor --fix` behaviour: a comment-only placeholder
    # that loads as empty YAML.
    placeholder = config_dir / "citation_styles.yaml"
    placeholder.write_text("# TODO: restore BookMem configuration.\n", encoding="utf-8")

    before = check_config_files(fix=False)
    assert before.status == "FAIL", "an empty placeholder should not pass the config check"

    result = check_config_files(fix=True)
    assert result.status == "OK", result.message

    data = yaml.safe_load(placeholder.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and data.get("styles"), "config was not restored with real content"
