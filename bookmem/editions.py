"""Edition and work identity handling for BookMem."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
import re
from typing import Any

from .frontmatter import discover_book_files, read_markdown_with_frontmatter, write_markdown_with_frontmatter


EDITION_VERSION = "0.1.0"


@dataclass
class EditionRecord:
    path: str
    book_id: str | None
    title: str
    author: str | None
    isbn: str | None
    work_id: str
    canonical_title: str
    edition_label: str | None
    edition_number: int | None
    edition_year: int | None
    is_revised: bool
    primary_class: str | None


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"^the\s+", "", value)
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_") or "untitled"


def canonicalise_title(title: str) -> str:
    title = re.sub(r"\b(?:second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|revised|expanded|updated)\s+edition\b", "", title, flags=re.I)
    title = re.sub(r"\b\d+(?:st|nd|rd|th)\s+edition\b", "", title, flags=re.I)
    title = re.sub(r"\banniversary\s+edition\b", "", title, flags=re.I)
    title = re.sub(r"[,:\-–—]\s*(?:revised|expanded|updated|second|third|fourth|fifth).*$", "", title, flags=re.I)
    title = re.sub(r"\s+", " ", title).strip(" -–—,:")
    return title or "Untitled"


def _ordinal_suffix(number: int) -> str:
    if 10 <= number % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")


def infer_edition_from_title(title: str, published: Any = None) -> dict[str, Any]:
    text = title or ""
    edition: dict[str, Any] = {}
    patterns = [
        (r"\bsecond\s+edition\b", 2, "Second Edition"),
        (r"\bthird\s+edition\b", 3, "Third Edition"),
        (r"\bfourth\s+edition\b", 4, "Fourth Edition"),
        (r"\bfifth\s+edition\b", 5, "Fifth Edition"),
        (r"\bsixth\s+edition\b", 6, "Sixth Edition"),
        (r"\bseventh\s+edition\b", 7, "Seventh Edition"),
        (r"\beighth\s+edition\b", 8, "Eighth Edition"),
        (r"\bninth\s+edition\b", 9, "Ninth Edition"),
        (r"\btenth\s+edition\b", 10, "Tenth Edition"),
    ]
    for pattern, number, label in patterns:
        if re.search(pattern, text, flags=re.I):
            edition["label"] = label
            edition["number"] = number
            break

    ordinal = re.search(r"\b(\d+)(?:st|nd|rd|th)\s+edition\b", text, flags=re.I)
    if ordinal and "number" not in edition:
        number = int(ordinal.group(1))
        edition["number"] = number
        edition["label"] = f"{number}{_ordinal_suffix(number)} Edition"

    if re.search(r"\brevised\b", text, flags=re.I):
        edition["is_revised"] = True
    if re.search(r"\bexpanded\b|\bupdated\b", text, flags=re.I):
        edition["is_revised"] = True

    year = None
    if published:
        match = re.search(r"\b(19|20)\d{2}\b", str(published))
        if match:
            year = int(match.group(0))
    if year:
        edition["year"] = year

    edition.setdefault("is_revised", False)
    return edition


def isbn_from_frontmatter(frontmatter: dict[str, Any]) -> str | None:
    isbn = frontmatter.get("isbn")
    if isinstance(isbn, dict):
        for value in isbn.values():
            if value:
                return re.sub(r"[^0-9Xx]", "", str(value))
    if isbn:
        return re.sub(r"[^0-9Xx]", "", str(isbn))
    return None


def work_from_frontmatter(path: Path, frontmatter: dict[str, Any]) -> dict[str, Any]:
    existing = frontmatter.get("work") if isinstance(frontmatter.get("work"), dict) else {}
    title = str(frontmatter.get("title") or path.stem)
    author = str(frontmatter.get("author") or "")
    canonical_title = str(existing.get("canonical_title") or canonicalise_title(title))
    work_id = str(existing.get("work_id") or slugify(f"{author}_{canonical_title}" if author else canonical_title))
    return {"work_id": work_id, "canonical_title": canonical_title}


def edition_from_frontmatter(frontmatter: dict[str, Any]) -> dict[str, Any]:
    existing = frontmatter.get("edition") if isinstance(frontmatter.get("edition"), dict) else {}
    title = str(frontmatter.get("title") or "")
    inferred = infer_edition_from_title(title, frontmatter.get("published"))
    merged = dict(inferred)
    merged.update(existing)
    return merged


def ensure_work_edition_frontmatter(path: Path, write: bool = False, overwrite: bool = False) -> tuple[dict[str, Any], bool]:
    frontmatter, body, had = read_markdown_with_frontmatter(path)
    changed = False

    if overwrite or not isinstance(frontmatter.get("work"), dict):
        work = work_from_frontmatter(path, frontmatter)
        if frontmatter.get("work") != work:
            frontmatter["work"] = work
            changed = True
    else:
        # Fill missing subfields without replacing reviewed values.
        work = frontmatter["work"]
        inferred = work_from_frontmatter(path, frontmatter)
        for key, value in inferred.items():
            if not work.get(key):
                work[key] = value
                changed = True

    if overwrite or not isinstance(frontmatter.get("edition"), dict):
        edition = edition_from_frontmatter(frontmatter)
        if edition:
            if frontmatter.get("edition") != edition:
                frontmatter["edition"] = edition
                changed = True
    else:
        edition = frontmatter["edition"]
        inferred = edition_from_frontmatter(frontmatter)
        for key, value in inferred.items():
            if key not in edition:
                edition[key] = value
                changed = True

    metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
    metadata["edition_handling_version"] = EDITION_VERSION
    frontmatter["metadata"] = metadata

    if write and changed:
        write_markdown_with_frontmatter(path, frontmatter, body)

    return frontmatter, changed


def edition_record_from_file(path: Path, ensure: bool = False) -> EditionRecord:
    if ensure:
        frontmatter, _changed = ensure_work_edition_frontmatter(path, write=False)
    else:
        frontmatter, _body, _had = read_markdown_with_frontmatter(path)

    work = work_from_frontmatter(path, frontmatter)
    edition = edition_from_frontmatter(frontmatter)
    classification = frontmatter.get("classification") if isinstance(frontmatter.get("classification"), dict) else {}

    return EditionRecord(
        path=str(path),
        book_id=frontmatter.get("book_id"),
        title=str(frontmatter.get("title") or path.stem),
        author=str(frontmatter.get("author")) if frontmatter.get("author") else None,
        isbn=isbn_from_frontmatter(frontmatter),
        work_id=str(work.get("work_id")),
        canonical_title=str(work.get("canonical_title")),
        edition_label=edition.get("label"),
        edition_number=edition.get("number"),
        edition_year=edition.get("year"),
        is_revised=bool(edition.get("is_revised", False)),
        primary_class=classification.get("primary_class"),
    )


def list_editions(books_dir: Path, query: str | None = None, ensure: bool = False) -> list[EditionRecord]:
    records: list[EditionRecord] = []
    query_norm = slugify(query) if query else None

    for path in discover_book_files(books_dir):
        record = edition_record_from_file(path, ensure=ensure)
        if query_norm:
            haystack = slugify(" ".join([
                record.title,
                record.author or "",
                record.canonical_title,
                record.work_id,
                record.isbn or "",
            ]))
            if query_norm not in haystack:
                continue
        records.append(record)

    return sorted(records, key=lambda r: (r.canonical_title.lower(), r.edition_year or 0, r.edition_number or 0, r.title.lower()))


def group_editions(records: list[EditionRecord]) -> dict[str, list[EditionRecord]]:
    grouped: dict[str, list[EditionRecord]] = defaultdict(list)
    for record in records:
        grouped[record.work_id].append(record)
    return dict(grouped)


def edition_records_as_dict(records: list[EditionRecord]) -> list[dict[str, Any]]:
    return [asdict(record) for record in records]


def classify_duplicate_relationship(a: EditionRecord, b: EditionRecord) -> str:
    """Classify the relationship between two edition records."""
    if a.isbn and b.isbn and a.isbn == b.isbn:
        return "same ISBN, duplicate"
    if a.work_id == b.work_id:
        if (a.edition_number and b.edition_number and a.edition_number != b.edition_number) or (a.edition_year and b.edition_year and a.edition_year != b.edition_year):
            return "same work, different edition"
        return "same work, possible duplicate"
    if slugify(a.title) == slugify(b.title) and slugify(a.author or "") == slugify(b.author or ""):
        return "same title/author, maybe duplicate"
    return "different work"
