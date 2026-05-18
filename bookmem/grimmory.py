"""Grimmory sidecar/export support for BookMem.

BookMem does not write into Grimmory's database. It exports files and
sidecar-style JSON that Grimmory can use when sidecar metadata is enabled or
preferred for a library.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import shutil
from typing import Any

from .frontmatter import discover_book_files, read_markdown_with_frontmatter


GRIMMORY_EXPORT_VERSION = "0.1.0"


@dataclass
class GrimmoryExportResult:
    source_path: str
    output_book_path: str | None
    sidecar_path: str
    title: str
    authors: list[str]


INVALID_FILENAME_CHARS_RE = re.compile(r'[\\/:*?"<>|]')
MULTI_SPACE_RE = re.compile(r"\s+")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_filename_part(value: str | None, fallback: str = "Untitled") -> str:
    value = (value or fallback).strip()
    value = INVALID_FILENAME_CHARS_RE.sub(" ", value)
    value = value.replace("\n", " ").replace("\r", " ")
    value = MULTI_SPACE_RE.sub(" ", value).strip(" .")
    return value or fallback


def _authors(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _isbn_values(frontmatter: dict[str, Any]) -> tuple[str | None, str | None]:
    isbn = frontmatter.get("isbn")
    values: list[str] = []
    if isinstance(isbn, dict):
        values = [str(v) for v in isbn.values() if v]
    elif isbn:
        values = [str(isbn)]
    isbn10 = None
    isbn13 = None
    for value in values:
        compact = re.sub(r"[^0-9Xx]", "", value)
        if len(compact) == 10 and not isbn10:
            isbn10 = compact
        if len(compact) == 13 and not isbn13:
            isbn13 = compact
    return isbn10, isbn13


def grimmory_metadata_from_frontmatter(book_path: Path) -> dict[str, Any]:
    frontmatter, body, _had = read_markdown_with_frontmatter(book_path)
    classification = frontmatter.get("classification") if isinstance(frontmatter.get("classification"), dict) else {}
    metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
    isbn10, isbn13 = _isbn_values(frontmatter)

    title = str(frontmatter.get("title") or book_path.stem)
    subtitle = frontmatter.get("subtitle")
    authors = _authors(frontmatter.get("author"))
    tags = frontmatter.get("tags") or classification.get("topics") or []
    if not isinstance(tags, list):
        tags = [str(tags)]

    series = frontmatter.get("series") if isinstance(frontmatter.get("series"), dict) else {}

    return {
        "version": "1.0",
        "generatedBy": "BookMem",
        "generatedAt": utc_now_iso(),
        "source": {
            "provider": "bookmem",
            "bookmemVersion": GRIMMORY_EXPORT_VERSION,
            "sourceBook": str(book_path),
            "bookId": frontmatter.get("book_id"),
        },
        "title": title,
        "subtitle": subtitle,
        "authors": authors,
        "publisher": frontmatter.get("publisher"),
        "publishedDate": frontmatter.get("published"),
        "description": metadata.get("description") or metadata.get("summary"),
        "isbn10": isbn10,
        "isbn13": isbn13,
        "language": frontmatter.get("language"),
        "categories": tags,
        "series": {
            "name": series.get("name"),
            "index": series.get("index"),
        } if series else None,
        "tags": tags,
        "identifiers": {
            "bookmem": frontmatter.get("book_id"),
            "bmdc": classification.get("primary_class"),
        },
        "bookmem": {
            "primaryClass": classification.get("primary_class"),
            "primaryLabel": classification.get("primary_label"),
            "routingAliases": classification.get("routing_aliases", []),
            "topics": classification.get("topics", []),
        },
    }


def sidecar_name_for(book_file: Path) -> str:
    return f"{book_file.stem}.metadata.json"


def write_grimmory_sidecar(book_path: Path, output_dir: Path | None = None, overwrite: bool = False) -> Path:
    output_dir = output_dir or book_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / sidecar_name_for(book_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"Sidecar already exists: {target}")
    data = grimmory_metadata_from_frontmatter(book_path)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def export_grimmory_library(
    books_dir: Path,
    output_dir: Path,
    copy_markdown: bool = False,
    overwrite: bool = False,
) -> list[GrimmoryExportResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[GrimmoryExportResult] = []

    for book_path in discover_book_files(books_dir):
        fm, _body, _had = read_markdown_with_frontmatter(book_path)
        title = str(fm.get("title") or book_path.stem)
        authors = _authors(fm.get("author"))
        folder_name = safe_filename_part(" - ".join([title, ", ".join(authors)] if authors else [title]))
        book_folder = output_dir / folder_name
        book_folder.mkdir(parents=True, exist_ok=True)

        copied_book_path: Path | None = None
        if copy_markdown:
            copied_book_path = book_folder / book_path.name
            if copied_book_path.exists() and not overwrite:
                raise FileExistsError(f"Book already exists: {copied_book_path}")
            shutil.copy2(book_path, copied_book_path)

        sidecar_source_path = copied_book_path or (book_folder / book_path.name)
        # Write sidecar with same stem as copied/expected book file.
        data = grimmory_metadata_from_frontmatter(book_path)
        sidecar = book_folder / sidecar_name_for(sidecar_source_path)
        if sidecar.exists() and not overwrite:
            raise FileExistsError(f"Sidecar already exists: {sidecar}")
        sidecar.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        results.append(
            GrimmoryExportResult(
                source_path=str(book_path),
                output_book_path=str(copied_book_path) if copied_book_path else None,
                sidecar_path=str(sidecar),
                title=title,
                authors=authors,
            )
        )

    return results


def result_as_dict(result: GrimmoryExportResult) -> dict[str, Any]:
    return asdict(result)
