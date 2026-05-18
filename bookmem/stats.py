from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .chunking import FRONTMATTER_RE, metadata_from_frontmatter, parse_frontmatter, slugify
from .config import get_settings
from .manifest import get_record_for_path, load_manifest, manifest_path, markdown_hashes
from .taxonomy import get_class_label, normalise_alias

STATS_VERSION = "0.1.0"


@dataclass
class BookStat:
    path: Path
    book_id: str
    title: str
    author: str | None
    primary_class: str
    primary_class_label: str
    secondary_classes: list[str]
    routing_aliases: list[str]
    topics: list[str]
    isbns: list[str]
    indexed: bool
    chunk_count: int
    content_changed: bool
    frontmatter_changed: bool
    classification_source: str


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        if "|" in value:
            return [item.strip() for item in value.split("|") if item.strip()]
        return [value.strip()] if value.strip() else []
    return [str(value).strip()] if str(value).strip() else []


def _isbn_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [str(item).strip() for item in value.values() if str(item).strip()]
    return _as_list(value)


def _record_for_path(path: Path) -> dict[str, Any] | None:
    try:
        return get_record_for_path(path)
    except Exception:
        return None


def load_book_stats(books_dir: Path | None = None) -> list[BookStat]:
    settings = get_settings()
    root = books_dir or settings.books_dir
    files = sorted(set(root.glob("*.md")) | set(root.glob("**/*.md")))
    stats: list[BookStat] = []

    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        frontmatter, _body = parse_frontmatter(text)
        metadata = metadata_from_frontmatter(path, root, frontmatter)
        classification = frontmatter.get("classification") if isinstance(frontmatter.get("classification"), dict) else {}
        meta_block = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}

        title = str(metadata.get("title") or frontmatter.get("title") or path.stem).strip()
        author_value = metadata.get("author") or frontmatter.get("author")
        author = str(author_value).strip() if author_value else None
        book_id = slugify(f"{author or ''}_{title}")

        primary_class = str(metadata.get("primary_class") or classification.get("primary_class") or "999")
        primary_label = str(metadata.get("primary_class_label") or classification.get("primary_label") or get_class_label(primary_class))
        secondary_classes = _as_list(classification.get("secondary_classes") or classification.get("secondary_class"))
        routing_aliases = _as_list(classification.get("routing_aliases"))
        topics = _as_list(classification.get("topics") or frontmatter.get("topics"))
        isbns = sorted(set(_isbn_values(frontmatter.get("isbn"))))

        record = _record_for_path(path) or {}
        content_hash, frontmatter_hash, _full_hash = markdown_hashes(path)
        indexed = bool(record.get("last_indexed"))
        chunk_count = int(record.get("chunk_count") or 0)
        content_changed = not record or record.get("content_hash") != content_hash
        frontmatter_changed = not record or record.get("frontmatter_hash") != frontmatter_hash
        classification_source = str(meta_block.get("classification_source") or record.get("classification_source") or "")

        stats.append(
            BookStat(
                path=path,
                book_id=book_id,
                title=title,
                author=author,
                primary_class=primary_class,
                primary_class_label=primary_label,
                secondary_classes=secondary_classes,
                routing_aliases=routing_aliases,
                topics=topics,
                isbns=isbns,
                indexed=indexed,
                chunk_count=chunk_count,
                content_changed=content_changed,
                frontmatter_changed=frontmatter_changed,
                classification_source=classification_source,
            )
        )

    return stats


def collection_totals(stats: list[BookStat]) -> dict[str, Any]:
    return {
        "books": len(stats),
        "indexed_books": sum(1 for book in stats if book.indexed),
        "books_needing_index": sum(1 for book in stats if not book.indexed or book.content_changed or book.frontmatter_changed),
        "indexed_chunks": sum(book.chunk_count for book in stats),
        "unclassified_books": sum(1 for book in stats if book.primary_class == "999"),
        "books_without_author": sum(1 for book in stats if not book.author),
        "books_without_topics": sum(1 for book in stats if not book.topics),
        "books_with_isbn": sum(1 for book in stats if book.isbns),
    }


def class_counts(stats: list[BookStat]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for book in stats:
        item = grouped.setdefault(
            book.primary_class,
            {
                "class_code": book.primary_class,
                "label": book.primary_class_label or get_class_label(book.primary_class),
                "books": 0,
                "chunks": 0,
                "authors": set(),
            },
        )
        item["books"] += 1
        item["chunks"] += book.chunk_count
        if book.author:
            item["authors"].add(book.author)
    rows = []
    for item in grouped.values():
        rows.append({**item, "authors": len(item["authors"])})
    return sorted(rows, key=lambda row: (-row["books"], row["class_code"]))


def author_counts(stats: list[BookStat]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for book in stats:
        author = book.author or "Unknown author"
        item = grouped.setdefault(author, {"author": author, "books": 0, "chunks": 0, "classes": set()})
        item["books"] += 1
        item["chunks"] += book.chunk_count
        item["classes"].add(book.primary_class)
    rows = []
    for item in grouped.values():
        rows.append({**item, "classes": ", ".join(sorted(item["classes"]))})
    return sorted(rows, key=lambda row: (-row["books"], row["author"].lower()))


def topic_counts(stats: list[BookStat]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for book in stats:
        for topic in book.topics:
            key = normalise_alias(topic).replace("_", " ")
            if not key:
                continue
            item = grouped.setdefault(key, {"topic": key, "books": 0, "chunks": 0, "classes": set()})
            item["books"] += 1
            item["chunks"] += book.chunk_count
            item["classes"].add(book.primary_class)
    rows = []
    for item in grouped.values():
        rows.append({**item, "classes": ", ".join(sorted(item["classes"]))})
    return sorted(rows, key=lambda row: (-row["books"], row["topic"]))


def stats_payload(stats: list[BookStat], limit: int = 20) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "stats_version": STATS_VERSION,
        "totals": collection_totals(stats),
        "top_classes": class_counts(stats)[:limit],
        "top_authors": author_counts(stats)[:limit],
        "top_topics": topic_counts(stats)[:limit],
    }
