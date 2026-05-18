"""0002_add_index_metadata

Add manifest-level index metadata for installations that predate index
version tracking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import json


ID = "0002_add_index_metadata"
DESCRIPTION = "Add manifest-level index metadata placeholder."
VERSION = 1


def apply(context: dict[str, Any]) -> dict[str, Any]:
    root = Path(context.get("root", "."))
    path = root / "data" / "manifests" / "books.json"
    if not path.exists():
        return {"skipped": "books manifest not present"}

    data = json.loads(path.read_text(encoding="utf-8"))
    changed = False

    if "index_metadata" not in data:
        data["index_metadata"] = {
            "migration_note": "Added by 0002_add_index_metadata. Run `bookmem ingest --changed-only` or `bookmem index-status --update-manifest` to populate current values."
        }
        changed = True

    if changed:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {"changed": changed, "path": str(path)}
