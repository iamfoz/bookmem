from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Any

import yaml

from .chunking import slugify
from .config import get_settings
from .frontmatter import read_markdown_with_frontmatter
from .book_files import discover_book_markdown_files
from .manifest import get_record_for_path
from .search import format_markdown_citation, format_source_location, get_table
from .summaries import summaries_root

AGENT_EXPORT_VERSION = "0.1.0"
SUPPORTED_AGENT_EXPORT_FORMATS = {"jsonl", "llamaindex", "langchain", "markdown-index"}


@dataclass
class AgentExportResult:
    format: str
    output_dir: Path
    files: list[Path]
    book_count: int
    chunk_count: int


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalise_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        if "|" in value:
            return [item.strip() for item in value.split("|") if item.strip()]
        return [value.strip()] if value.strip() else []
    return [str(value).strip()] if str(value).strip() else []


def _first_isbn(meta: dict[str, Any]) -> str | None:
    value = meta.get("isbn")
    if isinstance(value, dict):
        for preferred in ("filename", "detected_in_text", "loc", "unknown"):
            if value.get(preferred):
                return str(value[preferred])
        for item in value.values():
            if item:
                return str(item)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _safe_metadata_value(value: Any) -> Any:
    """Convert values to JSON-safe primitives for downstream agent frameworks."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_safe_metadata_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _safe_metadata_value(item) for key, item in value.items()}
    return str(value)


def _load_summary(book_id: str) -> dict[str, Any]:
    path = summaries_root() / book_id / "book.yaml"
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _load_chapter_summaries(book_id: str) -> list[dict[str, Any]]:
    path = summaries_root() / book_id / "chapters.yaml"
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    chapters = data.get("chapters", []) if isinstance(data, dict) else []
    return [item for item in chapters if isinstance(item, dict)]


def _book_record_from_markdown(path: Path, books_root: Path) -> dict[str, Any]:
    meta, _body, _had_frontmatter = read_markdown_with_frontmatter(path)
    title = str(meta.get("title") or path.stem).strip()
    author = meta.get("author")
    author = str(author).strip() if author else None
    book_id = slugify(f"{author or ''}_{title}")

    classification = meta.get("classification") if isinstance(meta.get("classification"), dict) else {}
    primary_class = str(classification.get("primary_class") or meta.get("primary_class") or "999")
    primary_label = str(classification.get("primary_label") or meta.get("primary_class_label") or "Unclassified")
    secondary_classes = _normalise_list(classification.get("secondary_classes") or classification.get("secondary_class") or meta.get("secondary_classes"))
    routing_aliases = _normalise_list(classification.get("routing_aliases") or meta.get("routing_aliases"))
    topics = _normalise_list(classification.get("topics") or meta.get("topics"))
    classification_source = str(classification.get("source") or meta.get("classification_source") or "")

    summary = _load_summary(book_id)
    chapters = _load_chapter_summaries(book_id)
    manifest_record = get_record_for_path(path)

    try:
        relative_path = str(path.relative_to(books_root))
    except Exception:
        relative_path = str(path)

    return {
        "book_id": book_id,
        "title": title,
        "author": author,
        "isbn": _first_isbn(meta),
        "source_path": str(path),
        "relative_path": relative_path,
        "primary_class": primary_class,
        "primary_class_label": primary_label,
        "secondary_classes": secondary_classes,
        "routing_aliases": routing_aliases,
        "topics": topics,
        "classification_source": classification_source,
        "summary": {
            "core_thesis": summary.get("core_thesis"),
            "major_ideas": summary.get("major_ideas", []),
            "best_for_questions_about": summary.get("best_for_questions_about", []),
            "summary_path": str((summaries_root() / book_id / "book.yaml")) if summary else None,
        },
        "chapter_count": len(chapters),
        "chapters": [
            {
                "chapter_id": chapter.get("chapter_id"),
                "title": chapter.get("title"),
                "major_ideas": chapter.get("major_ideas", []),
                "keywords": chapter.get("keywords", []),
            }
            for chapter in chapters
        ],
        "manifest": manifest_record or {},
    }


def collect_books(books_dir: Path | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    root = books_dir or settings.books_dir
    if not root.exists():
        return []
    books = [_book_record_from_markdown(path, root) for path in discover_book_markdown_files(root)]
    return sorted(books, key=lambda item: (str(item.get("primary_class", "")), str(item.get("title", "")).lower()))


def collect_chunks() -> list[dict[str, Any]]:
    try:
        table = get_table()
        rows = table.to_pandas()
    except Exception:
        return []

    if rows.empty:
        return []

    records: list[dict[str, Any]] = []
    for row in rows.sort_values(["book_id", "chunk_index"]).to_dict(orient="records"):
        record = {str(key): _safe_metadata_value(value) for key, value in row.items()}
        # Embedding vectors are useful inside LanceDB but usually not useful in portable exports.
        record.pop("vector", None)
        record["source_location"] = format_source_location(record)
        record["citation"] = format_markdown_citation(record)
        records.append(record)
    return records


def _write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def _chunk_metadata(chunk: dict[str, Any], include_text: bool = False) -> dict[str, Any]:
    excluded = {"text", "_distance", "_score"}
    if not include_text:
        excluded.add("vector")
    metadata = {key: value for key, value in chunk.items() if key not in excluded}
    return {str(key): _safe_metadata_value(value) for key, value in metadata.items()}


def _export_jsonl(chunks: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    return [_write_jsonl(output_dir / "bookmem_chunks.jsonl", chunks)]


def _export_llamaindex(chunks: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    records = []
    for chunk in chunks:
        records.append(
            {
                "id_": chunk.get("chunk_id"),
                "text": chunk.get("text", ""),
                "metadata": _chunk_metadata(chunk),
            }
        )
    return [_write_jsonl(output_dir / "bookmem_llamaindex_documents.jsonl", records)]


def _export_langchain(chunks: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    records = []
    for chunk in chunks:
        records.append(
            {
                "page_content": chunk.get("text", ""),
                "metadata": _chunk_metadata(chunk),
            }
        )
    return [_write_jsonl(output_dir / "bookmem_langchain_documents.jsonl", records)]


def _slug_filename(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or "untitled"


def _export_markdown_index(books: list[dict[str, Any]], chunks: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "bookmem_agent_tools.md"

    class_counts: dict[str, int] = {}
    for book in books:
        code = str(book.get("primary_class") or "999")
        class_counts[code] = class_counts.get(code, 0) + 1

    lines = [
        "# BookMem Agent Index",
        "",
        f"Generated: {utc_now_iso()}",
        f"Books: {len(books)}",
        f"Indexed chunks: {len(chunks)}",
        "",
        "## How to use this corpus",
        "",
        "Use BookMem as a retrieval layer rather than as a source of unsupported claims.",
        "Search first, inspect the strongest hits, read around the strongest chunks, then cite the source location and chunk ID.",
        "",
        "Recommended tool flow:",
        "",
        "```bash",
        "bookmem route \"<question>\"",
        "bookmem ask-search \"<question>\" --summaries-first",
        "bookmem read-around \"<chunk_id>\" --before 2 --after 3",
        "bookmem read-section --chunk-id \"<chunk_id>\"",
        "bookmem read-chapter --book \"<book_id>\" --chapter \"<chapter title>\"",
        "```",
        "",
        "Rules for agents:",
        "",
        "- Prefer routed search over broad search.",
        "- Prefer summary maps to choose which books to inspect.",
        "- Do not claim a book says something unless retrieved text supports it.",
        "- Include title, author, heading, line range and chunk ID when citing evidence.",
        "- Broaden the search only when routed results are weak or absent.",
        "",
        "## Class distribution",
        "",
    ]

    for code, count in sorted(class_counts.items()):
        label = next((book.get("primary_class_label") for book in books if str(book.get("primary_class")) == code), "")
        lines.append(f"- `{code}` {label}: {count} book(s)")

    lines.extend(["", "## Books", ""])
    for book in books:
        aliases = ", ".join(book.get("routing_aliases", []) or [])
        topics = ", ".join(book.get("topics", []) or [])
        lines.extend(
            [
                f"### {book.get('title')}",
                "",
                f"- Author: {book.get('author') or 'Unknown'}",
                f"- Book ID: `{book.get('book_id')}`",
                f"- Class: `{book.get('primary_class')}` {book.get('primary_class_label')}",
                f"- Source: `{book.get('relative_path') or book.get('source_path')}`",
            ]
        )
        if book.get("isbn"):
            lines.append(f"- ISBN: `{book.get('isbn')}`")
        if aliases:
            lines.append(f"- Routing aliases: {aliases}")
        if topics:
            lines.append(f"- Topics: {topics}")
        summary = book.get("summary") or {}
        if summary.get("core_thesis"):
            lines.extend(["", str(summary.get("core_thesis"))])
        if summary.get("best_for_questions_about"):
            lines.append("")
            lines.append("Best for questions about: " + ", ".join(summary.get("best_for_questions_about") or []))
        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return [path]


def export_agent_corpus(
    export_format: str,
    output_dir: Path | None = None,
    books_dir: Path | None = None,
) -> AgentExportResult:
    export_format = export_format.lower().strip()
    if export_format not in SUPPORTED_AGENT_EXPORT_FORMATS and export_format != "all":
        raise ValueError(
            f"Unsupported agent export format: {export_format}. "
            f"Supported: {', '.join(sorted(SUPPORTED_AGENT_EXPORT_FORMATS | {'all'}))}"
        )

    root = output_dir or Path("exports")
    root.mkdir(parents=True, exist_ok=True)

    books = collect_books(books_dir=books_dir)
    chunks = collect_chunks()

    files: list[Path] = []
    files.append(_write_json(root / "bookmem_books.json", books))
    files.append(
        _write_json(
            root / "bookmem_export_manifest.json",
            {
                "schema_version": 1,
                "exporter_version": AGENT_EXPORT_VERSION,
                "generated_at": utc_now_iso(),
                "format": export_format,
                "book_count": len(books),
                "chunk_count": len(chunks),
                "files": [],
            },
        )
    )

    selected = sorted(SUPPORTED_AGENT_EXPORT_FORMATS) if export_format == "all" else [export_format]
    for item in selected:
        if item == "jsonl":
            files.extend(_export_jsonl(chunks, root))
        elif item == "llamaindex":
            files.extend(_export_llamaindex(chunks, root))
        elif item == "langchain":
            files.extend(_export_langchain(chunks, root))
        elif item == "markdown-index":
            files.extend(_export_markdown_index(books, chunks, root))

    # Rewrite manifest now that we know all output files.
    _write_json(
        root / "bookmem_export_manifest.json",
        {
            "schema_version": 1,
            "exporter_version": AGENT_EXPORT_VERSION,
            "generated_at": utc_now_iso(),
            "format": export_format,
            "book_count": len(books),
            "chunk_count": len(chunks),
            "files": [str(path) for path in files if path.name != "bookmem_export_manifest.json"],
        },
    )

    # De-duplicate while preserving order.
    seen: set[Path] = set()
    unique_files: list[Path] = []
    for path in files:
        if path not in seen:
            unique_files.append(path)
            seen.add(path)

    return AgentExportResult(
        format=export_format,
        output_dir=root,
        files=unique_files,
        book_count=len(books),
        chunk_count=len(chunks),
    )
