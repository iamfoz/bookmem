"""0003_add_edition_fields

Add work/edition metadata placeholders only where safe.

This migration intentionally does not overwrite human-reviewed metadata and
does not infer complex edition history. The richer inference remains in
`bookmem editions --write`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import re
import yaml


ID = "0003_add_edition_fields"
DESCRIPTION = "Add safe work/edition placeholders to canonical book frontmatter."
VERSION = 1


def _slug(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"^the\s+", "", value)
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_") or "untitled"


def _split_frontmatter(text: str):
    if not text.startswith("---\n"):
        return {}, text, False
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text, False
    raw = text[4:end]
    body = text[end + 5:]
    return yaml.safe_load(raw) or {}, body, True


def _write_frontmatter(path: Path, frontmatter: dict, body: str) -> None:
    path.write_text(
        "---\n" + yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip() + "\n---\n" + body,
        encoding="utf-8",
    )


def apply(context: dict[str, Any]) -> dict[str, Any]:
    root = Path(context.get("root", "."))
    books_dir = root / "data" / "books"
    if not books_dir.exists():
        return {"skipped": "data/books not present"}

    changed_paths = []
    for path in sorted(books_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        frontmatter, body, had = _split_frontmatter(text)
        if not had:
            continue

        title = str(frontmatter.get("title") or path.stem)
        author = str(frontmatter.get("author") or "")
        changed = False

        if not isinstance(frontmatter.get("work"), dict):
            frontmatter["work"] = {
                "work_id": _slug(f"{author}_{title}" if author else title),
                "canonical_title": title,
            }
            changed = True

        if not isinstance(frontmatter.get("edition"), dict):
            frontmatter["edition"] = {
                "label": None,
                "number": None,
                "year": None,
                "is_revised": False,
            }
            changed = True

        if changed:
            _write_frontmatter(path, frontmatter, body)
            changed_paths.append(str(path))

    return {"changed": len(changed_paths), "paths": changed_paths[:100]}
