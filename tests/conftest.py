from __future__ import annotations

from pathlib import Path
import shutil

import pytest


@pytest.fixture
def fixture_root() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_library(tmp_path: Path, fixture_root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "bookmem"
    (root / "data" / "books").mkdir(parents=True)
    (root / "data" / "raw-books").mkdir(parents=True)
    (root / "data" / "lancedb").mkdir(parents=True)
    (root / "data" / "manifests").mkdir(parents=True)
    (root / "data" / "review").mkdir(parents=True)
    (root / "config").mkdir(parents=True)

    shutil.copytree(fixture_root / "cleaned", root / "data" / "books", dirs_exist_ok=True)
    shutil.copytree(fixture_root / "raw", root / "data" / "raw-books", dirs_exist_ok=True)

    monkeypatch.chdir(root)
    monkeypatch.setenv("BOOKMEM_BOOKS_DIR", str(root / "data" / "books"))
    monkeypatch.setenv("BOOKMEM_DB_DIR", str(root / "data" / "lancedb"))
    monkeypatch.setenv("BOOKMEM_TABLE", "book_chunks_test")
    return root
