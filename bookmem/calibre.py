"""Calibre metadata integration for BookMem.

Calibre is treated as a metadata source and import/audit source. It does not
replace canonical BookMem Markdown frontmatter.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import re
import sqlite3
from typing import Any

import yaml

from .frontmatter import read_markdown_with_frontmatter, write_markdown_with_frontmatter, discover_book_files


CALIBRE_INTEGRATION_VERSION = "0.1.0"


@dataclass
class CalibreBook:
    calibre_id: int
    title: str
    authors: list[str]
    path: str | None
    isbn: str | None
    publisher: str | None
    published: str | None
    series: str | None
    series_index: float | None
    tags: list[str]
    identifiers: dict[str, str]
    formats: list[str]


def _connect(calibre_library: Path) -> sqlite3.Connection:
    db_path = calibre_library / "metadata.db"
    if not db_path.exists():
        raise FileNotFoundError(f"Calibre metadata.db not found: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in str(value).split("||") if part and part.strip()]


def _identifiers_for(conn: sqlite3.Connection, book_id: int) -> dict[str, str]:
    try:
        rows = conn.execute(
            "SELECT type, val FROM identifiers WHERE book = ? ORDER BY type",
            (book_id,),
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    return {str(row["type"]): str(row["val"]) for row in rows if row["type"] and row["val"]}


def _formats_for(conn: sqlite3.Connection, book_id: int) -> list[str]:
    try:
        rows = conn.execute(
            "SELECT format FROM data WHERE book = ? ORDER BY format",
            (book_id,),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [str(row["format"]) for row in rows if row["format"]]


def _isbn_from_identifiers(identifiers: dict[str, str]) -> str | None:
    for key in ("isbn", "ISBN"):
        if identifiers.get(key):
            return identifiers[key]
    return None


def scan_calibre_library(calibre_library: Path) -> list[CalibreBook]:
    conn = _connect(calibre_library)
    try:
        rows = conn.execute(
            """
            SELECT
                b.id,
                b.title,
                b.path,
                b.pubdate,
                b.series_index,
                group_concat(DISTINCT a.name) AS authors,
                group_concat(DISTINCT t.name) AS tags,
                p.name AS publisher,
                s.name AS series
            FROM books b
            LEFT JOIN books_authors_link bal ON bal.book = b.id
            LEFT JOIN authors a ON a.id = bal.author
            LEFT JOIN books_tags_link btl ON btl.book = b.id
            LEFT JOIN tags t ON t.id = btl.tag
            LEFT JOIN publishers p ON p.id = b.publisher
            LEFT JOIN series s ON s.id = b.series
            GROUP BY b.id
            ORDER BY b.title
            """
        ).fetchall()

        books: list[CalibreBook] = []
        for row in rows:
            identifiers = _identifiers_for(conn, int(row["id"]))
            books.append(
                CalibreBook(
                    calibre_id=int(row["id"]),
                    title=str(row["title"] or ""),
                    authors=_split_csv(row["authors"]),
                    path=str(row["path"]) if row["path"] else None,
                    isbn=_isbn_from_identifiers(identifiers),
                    publisher=str(row["publisher"]) if row["publisher"] else None,
                    published=str(row["pubdate"]) if row["pubdate"] else None,
                    series=str(row["series"]) if row["series"] else None,
                    series_index=float(row["series_index"]) if row["series_index"] is not None else None,
                    tags=_split_csv(row["tags"]),
                    identifiers=identifiers,
                    formats=_formats_for(conn, int(row["id"])),
                )
            )
        return books
    finally:
        conn.close()


def normalise(value: str | None) -> str:
    value = (value or "").lower()
    value = re.sub(r"^the\s+", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def find_calibre_book(calibre_library: Path, query: str) -> list[CalibreBook]:
    q = normalise(query)
    books = scan_calibre_library(calibre_library)
    matches = []
    for book in books:
        haystack = " ".join([book.title, " ".join(book.authors), book.isbn or "", " ".join(book.tags)])
        if q in normalise(haystack):
            matches.append(book)
    return matches


def calibre_book_to_frontmatter_patch(book: CalibreBook) -> dict[str, Any]:
    patch: dict[str, Any] = {
        "title": book.title,
        "author": ", ".join(book.authors) if book.authors else None,
        "publisher": book.publisher,
        "published": book.published,
    }
    if book.isbn:
        patch["isbn"] = {"calibre": book.isbn}
    if book.series:
        patch["series"] = {"name": book.series, "index": book.series_index}
    if book.tags:
        patch["tags"] = book.tags

    patch["metadata"] = {
        "calibre": {
            "calibre_id": book.calibre_id,
            "path": book.path,
            "formats": book.formats,
            "identifiers": book.identifiers,
            "integration_version": CALIBRE_INTEGRATION_VERSION,
        }
    }
    return {key: value for key, value in patch.items() if value not in (None, [], {})}


def enrich_markdown_from_calibre(
    book_path: Path,
    calibre_library: Path,
    query: str | None = None,
    write: bool = False,
    overwrite: bool = False,
) -> tuple[dict[str, Any], CalibreBook | None]:
    frontmatter, body, had_frontmatter = read_markdown_with_frontmatter(book_path)
    query = query or str(frontmatter.get("isbn") or frontmatter.get("title") or book_path.stem)

    matches = find_calibre_book(calibre_library, query)
    if not matches:
        return frontmatter, None

    match = matches[0]
    patch = calibre_book_to_frontmatter_patch(match)

    for key, value in patch.items():
        if key == "metadata":
            existing = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
            existing.update(value)
            frontmatter["metadata"] = existing
            continue
        if overwrite or not frontmatter.get(key):
            frontmatter[key] = value

    if write:
        write_markdown_with_frontmatter(book_path, frontmatter, body)

    return frontmatter, match


def import_calibre_metadata_stubs(calibre_library: Path, output_dir: Path, overwrite: bool = False) -> list[Path]:
    from .importers import output_path_for_source, _frontmatter_block

    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for book in scan_calibre_library(calibre_library):
        source = Path((book.title or f"calibre-{book.calibre_id}") + ".md")
        output = output_path_for_source(source, output_dir, title=book.title, author=", ".join(book.authors), overwrite=overwrite)
        fm = calibre_book_to_frontmatter_patch(book)
        fm["bookmem_import"] = {
            "source_format": "calibre",
            "source_path": str(calibre_library / book.path) if book.path else str(calibre_library),
            "importer_version": CALIBRE_INTEGRATION_VERSION,
            "status": "metadata_stub",
        }
        body = f"# {book.title}\\n\\nImported from Calibre metadata. Import the source ebook file before preparing this as canonical BookMem content.\\n"
        output.write_text(_frontmatter_block(fm) + "\\n" + body, encoding="utf-8")
        paths.append(output)

    return paths


def calibre_book_as_dict(book: CalibreBook) -> dict[str, Any]:
    return asdict(book)
