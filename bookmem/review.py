from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .book_files import discover_book_markdown_files
from typing import Any

import yaml

from .config import get_settings
from .frontmatter import (
    find_isbns_in_text,
    normalise_isbn,
    read_markdown_with_frontmatter,
    write_markdown_with_frontmatter,
)
from .manifest import relative_or_absolute
from .prepare import canonical_filename
from .taxonomy import get_class_label, infer_class_from_path, normalise_alias

REVIEW_SCHEMA_VERSION = 1
REVIEW_GENERATOR_VERSION = "0.1.0"

REVIEW_FILES = {
    "metadata": "needs_metadata.yaml",
    "classification": "needs_classification.yaml",
    "low_confidence": "low_confidence_matches.yaml",
}

CLASSIFICATION_SOURCE_CONFIDENCE = {
    "manual_review": 1.0,
    "existing_frontmatter": 0.9,
    "library_of_congress_sru_isbn": 0.88,
    "folder_path": 0.72,
    "filename/content keyword": 0.55,
    "unclassified": 0.0,
    "unknown": 0.25,
    "missing_frontmatter": 0.0,
}

LOW_CONFIDENCE_THRESHOLD = 0.7


@dataclass
class ReviewSummary:
    review_dir: Path
    metadata_count: int
    classification_count: int
    low_confidence_count: int


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def review_root() -> Path:
    settings = get_settings()
    explicit = getattr(settings, "review_dir", None)
    if explicit:
        return explicit
    return settings.books_dir.parent / "review"


def review_file_path(queue: str, root: Path | None = None) -> Path:
    if queue not in REVIEW_FILES:
        raise ValueError(f"Unknown review queue: {queue}")
    return (root or review_root()) / REVIEW_FILES[queue]


def _safe_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, dict):
        return [str(item).strip() for item in value.values() if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        key = text.lower()
        if key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _base_class(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    return text[:3] if len(text) >= 3 and text[:3].isdigit() else None


def _book_id_from_frontmatter(path: Path, frontmatter: dict[str, Any]) -> str:
    from .chunking import slugify

    title = str(frontmatter.get("title") or path.stem).strip()
    author = str(frontmatter.get("author") or "").strip()
    return slugify(f"{author}_{title}")


def _classification_source(frontmatter: dict[str, Any]) -> str:
    metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
    return str(metadata.get("classification_source") or "unknown")


def _classification_confidence(frontmatter: dict[str, Any]) -> float:
    metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
    if metadata.get("classification_reviewed") is True:
        return 1.0
    explicit = metadata.get("classification_confidence")
    if explicit is not None:
        try:
            return float(explicit)
        except (TypeError, ValueError):
            pass
    return CLASSIFICATION_SOURCE_CONFIDENCE.get(_classification_source(frontmatter), 0.25)


def _isbn_values(frontmatter: dict[str, Any], body: str) -> list[str]:
    values: list[str] = []
    isbn = frontmatter.get("isbn")
    if isinstance(isbn, dict):
        values.extend(_safe_list(isbn))
    else:
        values.extend(_safe_list(isbn))
    metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
    values.extend(_safe_list(metadata.get("detected_text_isbns")))
    values.extend(find_isbns_in_text(body))
    normalised = [normalise_isbn(value) for value in values]
    return _unique([value for value in normalised if value])


def _loc_external_class(frontmatter: dict[str, Any]) -> tuple[str | None, str | None]:
    classification = frontmatter.get("classification") if isinstance(frontmatter.get("classification"), dict) else {}
    external = classification.get("external") if isinstance(classification.get("external"), dict) else {}
    loc = external.get("library_of_congress") if isinstance(external.get("library_of_congress"), dict) else {}
    return loc.get("normalised_class_number"), loc.get("raw_classification_number")


def _issue_base(path: Path, frontmatter: dict[str, Any]) -> dict[str, Any]:
    classification = frontmatter.get("classification") if isinstance(frontmatter.get("classification"), dict) else {}
    metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
    return {
        "book_id": _book_id_from_frontmatter(path, frontmatter),
        "path": relative_or_absolute(path),
        "title": frontmatter.get("title") or path.stem,
        "author": frontmatter.get("author"),
        "primary_class": classification.get("primary_class"),
        "primary_label": classification.get("primary_label"),
        "classification_source": metadata.get("classification_source") or "unknown",
    }


def scan_review_issues(books_dir: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    settings = get_settings()
    root = books_dir or settings.books_dir
    files = discover_book_markdown_files(root)

    metadata_issues: list[dict[str, Any]] = []
    classification_issues: list[dict[str, Any]] = []
    low_confidence_issues: list[dict[str, Any]] = []

    by_isbn: dict[str, list[Path]] = {}
    by_title_author: dict[str, list[Path]] = {}
    parsed: list[tuple[Path, dict[str, Any], str, list[str]]] = []

    for path in files:
        if ".staging" in path.parts:
            continue
        frontmatter, body, had_frontmatter = read_markdown_with_frontmatter(path)
        if not had_frontmatter:
            frontmatter = {
                "title": path.stem,
                "author": None,
                "classification": {"primary_class": "999", "primary_label": "Unclassified"},
                "metadata": {"classification_source": "missing_frontmatter"},
            }
        isbns = _isbn_values(frontmatter, body)
        parsed.append((path, frontmatter, body, isbns))

        for isbn in isbns:
            by_isbn.setdefault(isbn, []).append(path)

        title_key = str(frontmatter.get("title") or path.stem).strip().lower()
        author_key = str(frontmatter.get("author") or "").strip().lower()
        if title_key and author_key:
            by_title_author.setdefault(f"{title_key}|{author_key}", []).append(path)

    duplicate_paths: dict[Path, list[dict[str, Any]]] = {}
    for isbn, paths in by_isbn.items():
        unique_paths = sorted({p.resolve() for p in paths})
        if len(unique_paths) > 1:
            for path in paths:
                duplicate_paths.setdefault(path, []).append({
                    "type": "duplicate_isbn",
                    "isbn": isbn,
                    "matching_paths": [str(p) for p in unique_paths],
                })

    for _key, paths in by_title_author.items():
        unique_paths = sorted({p.resolve() for p in paths})
        if len(unique_paths) > 1:
            for path in paths:
                duplicate_paths.setdefault(path, []).append({
                    "type": "duplicate_title_author",
                    "matching_paths": [str(p) for p in unique_paths],
                })

    for path, frontmatter, _body, isbns in parsed:
        base = _issue_base(path, frontmatter)
        classification = frontmatter.get("classification") if isinstance(frontmatter.get("classification"), dict) else {}
        metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
        primary_class = str(classification.get("primary_class") or "999")
        confidence = _classification_confidence(frontmatter)
        source = _classification_source(frontmatter)

        if not frontmatter.get("author"):
            metadata_issues.append({
                **base,
                "issue": "no_author",
                "severity": "medium",
                "detail": "No author is present in the canonical frontmatter.",
                "review": {"status": "pending", "suggested_author": None},
            })

        if not frontmatter.get("title"):
            metadata_issues.append({
                **base,
                "issue": "no_title",
                "severity": "high",
                "detail": "No title is present in the canonical frontmatter.",
                "review": {"status": "pending", "suggested_title": path.stem},
            })

        if len(isbns) > 1:
            metadata_issues.append({
                **base,
                "issue": "multiple_isbns_found",
                "severity": "low",
                "detail": "Multiple checksum-valid ISBNs were found. Confirm which one should be canonical.",
                "isbns": isbns,
                "review": {"status": "pending", "canonical_isbn": isbns[0]},
            })

        for duplicate in duplicate_paths.get(path, []):
            metadata_issues.append({
                **base,
                "issue": duplicate["type"],
                "severity": "high",
                "detail": "Possible duplicate book already exists under another filename.",
                **{k: v for k, v in duplicate.items() if k != "type"},
                "review": {"status": "pending", "keep_path": base["path"]},
            })

        loc_class, loc_raw = _loc_external_class(frontmatter)
        if loc_class and _base_class(loc_class) and _base_class(primary_class) and _base_class(loc_class) != _base_class(primary_class):
            classification_issues.append({
                **base,
                "issue": "loc_class_conflict",
                "severity": "high",
                "detail": "External catalogue class conflicts with the current primary class.",
                "current_primary_class": primary_class,
                "external_class": loc_class,
                "external_raw_class": loc_raw,
                "review": {
                    "status": "pending",
                    "approved_primary_class": primary_class,
                    "approved_primary_label": get_class_label(_base_class(primary_class)) or classification.get("primary_label"),
                },
            })

        if primary_class == "999" or source in {"unclassified", "missing_frontmatter"}:
            suggested_class, suggested_label = infer_class_from_path(path, settings.books_dir)
            classification_issues.append({
                **base,
                "issue": "unclassified",
                "severity": "high",
                "detail": "The book is not classified and should be reviewed before indexing at scale.",
                "suggested_primary_class": suggested_class,
                "suggested_primary_label": suggested_label,
                "review": {
                    "status": "pending",
                    "approved_primary_class": suggested_class if suggested_class != "999" else None,
                    "approved_primary_label": suggested_label if suggested_class != "999" else None,
                },
            })
        elif confidence < LOW_CONFIDENCE_THRESHOLD:
            low_confidence_issues.append({
                **base,
                "issue": "classification_confidence_below_threshold",
                "severity": "medium",
                "detail": "Classification was assigned by a lower-confidence method and should be reviewed.",
                "confidence": round(confidence, 2),
                "threshold": LOW_CONFIDENCE_THRESHOLD,
                "review": {
                    "status": "pending",
                    "approved_primary_class": primary_class,
                    "approved_primary_label": classification.get("primary_label") or get_class_label(_base_class(primary_class)),
                },
            })

        if metadata.get("classification_review_required") is True:
            low_confidence_issues.append({
                **base,
                "issue": "classification_review_required",
                "severity": "medium",
                "detail": "Frontmatter explicitly marks this classification as requiring review.",
                "review": {
                    "status": "pending",
                    "approved_primary_class": primary_class,
                    "approved_primary_label": classification.get("primary_label") or get_class_label(_base_class(primary_class)),
                },
            })

    return {"metadata": metadata_issues, "classification": classification_issues, "low_confidence": low_confidence_issues}


def _queue_document(queue: str, issues: list[dict[str, Any]], books_dir: Path | None = None) -> dict[str, Any]:
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "generator_version": REVIEW_GENERATOR_VERSION,
        "queue": queue,
        "generated_at": utc_now_iso(),
        "books_dir": relative_or_absolute(books_dir or get_settings().books_dir),
        "issue_count": len(issues),
        "issues": issues,
    }


def write_review_queues(books_dir: Path | None = None, root: Path | None = None) -> ReviewSummary:
    review_dir = root or review_root()
    review_dir.mkdir(parents=True, exist_ok=True)
    issues = scan_review_issues(books_dir=books_dir)
    for queue, queue_issues in issues.items():
        path = review_file_path(queue, review_dir)
        path.write_text(
            yaml.safe_dump(_queue_document(queue, queue_issues, books_dir), sort_keys=False, allow_unicode=True, width=120),
            encoding="utf-8",
        )
    return ReviewSummary(review_dir, len(issues["metadata"]), len(issues["classification"]), len(issues["low_confidence"]))


def load_review_queue(queue: str, root: Path | None = None) -> dict[str, Any]:
    path = review_file_path(queue, root)
    if not path.exists():
        return _queue_document(queue, [])
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("queue", queue)
    data.setdefault("issues", [])
    return data


def _resolve_issue_path(issue: dict[str, Any]) -> Path:
    value = issue.get("path")
    if not value:
        raise ValueError("Issue has no path")
    path = Path(str(value))
    if path.exists():
        return path
    candidate = Path.cwd() / path
    if candidate.exists():
        return candidate
    return path


def apply_classification_reviews(root: Path | None = None) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    for queue in ("classification", "low_confidence"):
        data = load_review_queue(queue, root)
        for issue in data.get("issues", []):
            review = issue.get("review") if isinstance(issue.get("review"), dict) else {}
            if str(review.get("status", "")).lower() != "approved":
                continue
            approved_class = review.get("approved_primary_class")
            if not approved_class:
                continue
            path = _resolve_issue_path(issue)
            if not path.exists():
                applied.append({"path": str(path), "status": "missing"})
                continue
            frontmatter, body, had_frontmatter = read_markdown_with_frontmatter(path)
            if not had_frontmatter:
                applied.append({"path": str(path), "status": "missing_frontmatter"})
                continue
            classification = frontmatter.get("classification") if isinstance(frontmatter.get("classification"), dict) else {}
            base_code = _base_class(str(approved_class)) or str(approved_class)
            classification["primary_class"] = str(approved_class)
            classification["primary_label"] = review.get("approved_primary_label") or get_class_label(base_code) or classification.get("primary_label")
            if review.get("approved_secondary_classes") is not None:
                classification["secondary_classes"] = _safe_list(review.get("approved_secondary_classes"))
            if review.get("approved_routing_aliases") is not None:
                classification["routing_aliases"] = [normalise_alias(item) for item in _safe_list(review.get("approved_routing_aliases"))]
            if review.get("approved_topics") is not None:
                classification["topics"] = _safe_list(review.get("approved_topics"))
            frontmatter["classification"] = classification
            metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
            metadata["classification_source"] = "manual_review"
            metadata["classification_reviewed"] = True
            metadata["classification_confidence"] = 1.0
            metadata["classification_reviewed_at"] = utc_now_iso()
            metadata.pop("classification_review_required", None)
            frontmatter["metadata"] = metadata
            write_markdown_with_frontmatter(path, frontmatter, body)
            applied.append({"path": str(path), "status": "applied", "primary_class": str(approved_class)})
    return applied


def apply_metadata_reviews(root: Path | None = None) -> list[dict[str, Any]]:
    data = load_review_queue("metadata", root)
    applied: list[dict[str, Any]] = []
    for issue in data.get("issues", []):
        review = issue.get("review") if isinstance(issue.get("review"), dict) else {}
        if str(review.get("status", "")).lower() != "approved":
            continue
        path = _resolve_issue_path(issue)
        if not path.exists():
            applied.append({"path": str(path), "status": "missing"})
            continue
        frontmatter, body, had_frontmatter = read_markdown_with_frontmatter(path)
        if not had_frontmatter:
            applied.append({"path": str(path), "status": "missing_frontmatter"})
            continue
        changed = False
        if review.get("suggested_author"):
            frontmatter["author"] = str(review["suggested_author"]).strip()
            changed = True
        if review.get("suggested_title"):
            frontmatter["title"] = str(review["suggested_title"]).strip()
            changed = True
        if review.get("canonical_isbn"):
            isbn = frontmatter.get("isbn") if isinstance(frontmatter.get("isbn"), dict) else {}
            isbn["reviewed"] = str(review["canonical_isbn"])
            frontmatter["isbn"] = isbn
            changed = True
        if changed:
            write_markdown_with_frontmatter(path, frontmatter, body)
            applied.append({"path": str(path), "status": "applied"})
        else:
            applied.append({"path": str(path), "status": "no_change"})
    return applied


def apply_review_queue(root: Path | None = None) -> list[dict[str, Any]]:
    return apply_metadata_reviews(root) + apply_classification_reviews(root)


def canonical_filename_mismatches(books_dir: Path | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    root = books_dir or settings.books_dir
    mismatches: list[dict[str, Any]] = []
    for path in discover_book_markdown_files(root):
        frontmatter, _body, had_frontmatter = read_markdown_with_frontmatter(path)
        if not had_frontmatter:
            continue
        isbn_values = _safe_list(frontmatter.get("isbn"))
        isbn = isbn_values[0] if isbn_values else None
        expected = canonical_filename(str(frontmatter.get("title") or path.stem), str(frontmatter.get("author") or "") or None, isbn)
        if path.name != expected:
            mismatches.append({"path": relative_or_absolute(path), "expected_filename": expected, "current_filename": path.name})
    return mismatches
