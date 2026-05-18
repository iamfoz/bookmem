"""0001_initial

Establish the migration state file and ensure core manifest structure exists.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


ID = "0001_initial"
DESCRIPTION = "Initial migration baseline and manifest structure."
VERSION = 1


def apply(context: dict[str, Any]) -> dict[str, Any]:
    root = Path(context.get("root", "."))
    manifest_dir = root / "data" / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    books_manifest = manifest_dir / "books.json"
    if not books_manifest.exists():
        books_manifest.write_text(
            '{\n  "schema_version": 1,\n  "books": []\n}\n',
            encoding="utf-8",
        )

    return {
        "created_or_checked": [
            str(manifest_dir),
            str(books_manifest),
        ]
    }
