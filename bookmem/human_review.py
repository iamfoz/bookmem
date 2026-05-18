"""Human review workflow for machine-generated BookMem artefacts."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any

import yaml


HUMAN_REVIEW_VERSION = "0.1.0"

REVIEW_STATUSES = {
    "machine_draft",
    "needs_human_review",
    "human_reviewed",
    "rejected",
    "superseded",
}

REVIEW_LOG_PATH = Path("data/review/human_review_log.jsonl")


@dataclass
class MachineDraft:
    artefact_type: str
    id: str
    path: str
    title: str | None
    status: str
    detail: str | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_status(status: str) -> str:
    if status not in REVIEW_STATUSES:
        raise ValueError(f"Invalid review status: {status}. Expected one of: {', '.join(sorted(REVIEW_STATUSES))}")
    return status


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file is not a mapping: {path}")
    return data


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def append_review_log(action: str, target: str, status: str | None = None, detail: dict[str, Any] | None = None) -> None:
    REVIEW_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": utc_now_iso(),
        "action": action,
        "target": target,
        "status": status,
        "detail": detail or {},
        "human_review_version": HUMAN_REVIEW_VERSION,
    }
    with REVIEW_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def summary_paths(book_id: str) -> tuple[Path, Path]:
    base = Path("data/summaries") / book_id
    return base / "book.yaml", base / "chapters.yaml"


def concept_path(book_id: str) -> Path:
    return Path("data/concepts") / book_id / "concepts.yaml"


def load_concept_index() -> dict[str, Any]:
    path = Path("data/concepts/concepts.json")
    if not path.exists():
        return {"schema_version": 1, "concepts": []}
    return json.loads(path.read_text(encoding="utf-8"))


def write_concept_index(data: dict[str, Any]) -> None:
    path = Path("data/concepts/concepts.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def machine_drafts() -> list[MachineDraft]:
    drafts: list[MachineDraft] = []

    for path in sorted(Path("data/summaries").glob("*/book.yaml")):
        try:
            data = read_yaml(path)
        except Exception:
            continue
        status = str(data.get("review_status") or "")
        if status in {"machine_draft", "needs_human_review"}:
            drafts.append(
                MachineDraft(
                    artefact_type="summary",
                    id=str(data.get("book_id") or path.parent.name),
                    path=str(path),
                    title=data.get("title"),
                    status=status,
                    detail=data.get("generator") or data.get("provider"),
                )
            )

    for path in sorted(Path("data/concepts").glob("*/concepts.yaml")):
        try:
            data = read_yaml(path)
        except Exception:
            continue
        book_id = str(data.get("book_id") or path.parent.name)
        for concept in data.get("concepts", []) or []:
            if not isinstance(concept, dict):
                continue
            status = str(concept.get("review_status") or "")
            if status in {"machine_draft", "needs_human_review"}:
                drafts.append(
                    MachineDraft(
                        artefact_type="concept",
                        id=str(concept.get("concept_id") or ""),
                        path=str(path),
                        title=concept.get("name"),
                        status=status,
                        detail=f"{concept.get('title') or book_id} / {concept.get('type') or ''}",
                    )
                )

    # Generic YAML/Markdown files with review_status are handled by mark-human-reviewed, not scanned broadly here.
    return drafts


def set_summary_status(book_id: str, status: str = "human_reviewed", reviewer: str | None = None) -> dict[str, Any]:
    status = ensure_status(status)
    book_path, chapters_path = summary_paths(book_id)
    changed = []

    for path in (book_path, chapters_path):
        if not path.exists():
            continue
        data = read_yaml(path)
        data["review_status"] = status
        data["reviewed_at"] = utc_now_iso()
        if reviewer:
            data["reviewed_by"] = reviewer
        write_yaml(path, data)
        changed.append(str(path))

    if not changed:
        raise FileNotFoundError(f"No summary files found for book_id: {book_id}")

    append_review_log("set_summary_status", book_id, status, {"paths": changed, "reviewer": reviewer})
    return {"book_id": book_id, "status": status, "changed": changed}


def approve_summary(book_id: str, reviewer: str | None = None) -> dict[str, Any]:
    return set_summary_status(book_id, "human_reviewed", reviewer=reviewer)


def set_concepts_status(book_id: str, status: str = "human_reviewed", reviewer: str | None = None) -> dict[str, Any]:
    status = ensure_status(status)
    path = concept_path(book_id)
    if not path.exists():
        raise FileNotFoundError(f"No concept file found for book_id: {book_id}")

    data = read_yaml(path)
    changed = []
    for concept in data.get("concepts", []) or []:
        if not isinstance(concept, dict):
            continue
        concept["review_status"] = status
        concept["reviewed_at"] = utc_now_iso()
        if reviewer:
            concept["reviewed_by"] = reviewer
        changed.append(concept.get("concept_id"))

    data["review_status"] = status
    data["reviewed_at"] = utc_now_iso()
    if reviewer:
        data["reviewed_by"] = reviewer

    write_yaml(path, data)
    sync_concept_index_from_book_file(book_id)

    append_review_log("set_concepts_status", book_id, status, {"path": str(path), "reviewer": reviewer, "concept_count": len(changed)})
    return {"book_id": book_id, "status": status, "changed_concepts": changed, "path": str(path)}


def approve_concepts(book_id: str, reviewer: str | None = None) -> dict[str, Any]:
    return set_concepts_status(book_id, "human_reviewed", reviewer=reviewer)


def reject_concept(concept_id: str, reason: str | None = None, reviewer: str | None = None) -> dict[str, Any]:
    changed_paths = []

    for path in sorted(Path("data/concepts").glob("*/concepts.yaml")):
        data = read_yaml(path)
        changed = False
        for concept in data.get("concepts", []) or []:
            if not isinstance(concept, dict):
                continue
            if str(concept.get("concept_id")) == concept_id:
                concept["review_status"] = "rejected"
                concept["rejected_at"] = utc_now_iso()
                if reviewer:
                    concept["reviewed_by"] = reviewer
                if reason:
                    concept["rejection_reason"] = reason
                changed = True
        if changed:
            write_yaml(path, data)
            changed_paths.append(str(path))
            sync_concept_index_from_book_file(str(data.get("book_id") or path.parent.name))

    if not changed_paths:
        raise FileNotFoundError(f"Concept not found: {concept_id}")

    append_review_log("reject_concept", concept_id, "rejected", {"paths": changed_paths, "reason": reason, "reviewer": reviewer})
    return {"concept_id": concept_id, "status": "rejected", "changed": changed_paths, "reason": reason}


def mark_yaml_human_reviewed(path: Path, reviewer: str | None = None) -> dict[str, Any]:
    data = read_yaml(path)
    data["review_status"] = "human_reviewed"
    data["reviewed_at"] = utc_now_iso()
    if reviewer:
        data["reviewed_by"] = reviewer
    write_yaml(path, data)
    append_review_log("mark_human_reviewed", str(path), "human_reviewed", {"reviewer": reviewer})
    return {"path": str(path), "status": "human_reviewed"}


def mark_markdown_human_reviewed(path: Path, reviewer: str | None = None) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n"):
        raise ValueError(f"Markdown file has no YAML frontmatter: {path}")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError(f"Markdown file has malformed YAML frontmatter: {path}")

    raw = text[4:end]
    body = text[end + 5:]
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        data = {}

    data["review_status"] = "human_reviewed"
    data["reviewed_at"] = utc_now_iso()
    if reviewer:
        data["reviewed_by"] = reviewer

    path.write_text("---\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip() + "\n---\n" + body, encoding="utf-8")
    append_review_log("mark_human_reviewed", str(path), "human_reviewed", {"reviewer": reviewer})
    return {"path": str(path), "status": "human_reviewed"}


def mark_human_reviewed(path: Path, reviewer: str | None = None) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return mark_yaml_human_reviewed(path, reviewer=reviewer)
    if suffix in {".md", ".markdown"}:
        return mark_markdown_human_reviewed(path, reviewer=reviewer)
    raise ValueError(f"Unsupported file type for mark-human-reviewed: {path}")


def sync_concept_index_from_book_file(book_id: str) -> None:
    """Update concept index records for one book from its concepts.yaml."""
    source = concept_path(book_id)
    if not source.exists():
        return

    source_data = read_yaml(source)
    index = load_concept_index()
    concepts = index.get("concepts", [])
    if not isinstance(concepts, list):
        concepts = []

    # Remove old records for this book and re-add current ones.
    concepts = [c for c in concepts if not isinstance(c, dict) or str(c.get("book_id")) != book_id]
    for concept in source_data.get("concepts", []) or []:
        if isinstance(concept, dict):
            concepts.append(concept)

    index["concepts"] = concepts
    index["concept_count"] = len(concepts)
    index["updated_at"] = utc_now_iso()
    write_concept_index(index)


def drafts_as_dict(drafts: list[MachineDraft]) -> list[dict[str, Any]]:
    return [asdict(item) for item in drafts]
