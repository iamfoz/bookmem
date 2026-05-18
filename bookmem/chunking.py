from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import re
from typing import Any

import yaml

from .taxonomy import get_class_label, infer_class_from_path, normalise_alias


@dataclass
class Chunk:
    chunk_id: str
    book_id: str
    title: str
    author: str | None
    source_path: str
    heading_path: str
    chapter_id: str
    chapter_title: str
    section_id: str
    section_title: str
    start_line: int
    end_line: int
    citation: str
    chunk_index: int
    previous_chunk_id: str | None
    next_chunk_id: str | None
    text: str
    char_count: int
    content_hash: str
    primary_class: str
    primary_class_label: str
    secondary_class_text: str
    routing_aliases_text: str
    topics_text: str


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
CHUNKER_VERSION = "0.4.0"
INDEX_SCHEMA_VERSION = 3

CHAPTER_RE = re.compile(r"^(chapter\s+\d+|chapter\s+[ivxlcdm]+|preface|introduction|prologue|epilogue|conclusion|afterword|appendix\b.*)$", re.IGNORECASE)


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_") or "untitled"


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    raw = match.group(1)
    body = text[match.end():]
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        data = {}
    return data, body


def list_to_pipe(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return normalise_alias(value)
    if isinstance(value, list):
        return "|".join(normalise_alias(str(item)) for item in value if str(item).strip())
    return normalise_alias(str(value))


def metadata_from_frontmatter(path: Path, books_dir: Path, meta: dict[str, Any]) -> dict[str, Any]:
    title = str(meta.get("title") or path.stem).strip()
    author = meta.get("author")
    author = str(author).strip() if author else None

    classification = meta.get("classification") or {}
    if not isinstance(classification, dict):
        classification = {}

    inferred_class, inferred_label = infer_class_from_path(path, books_dir)
    primary_class = str(
        classification.get("primary_class") or meta.get("primary_class") or inferred_class
    )
    primary_class_label = str(
        classification.get("primary_label")
        or meta.get("primary_class_label")
        or get_class_label(primary_class)
        or inferred_label
    )

    secondary_class = classification.get("secondary_class") or meta.get("secondary_class") or []
    routing_aliases = classification.get("routing_aliases") or meta.get("routing_aliases") or []
    topics = classification.get("topics") or meta.get("topics") or []

    return {
        "title": title,
        "author": author,
        "primary_class": primary_class,
        "primary_class_label": primary_class_label,
        "secondary_class_text": list_to_pipe(secondary_class),
        "routing_aliases_text": list_to_pipe(routing_aliases),
        "topics_text": list_to_pipe(topics),
    }


def _clean_heading_title(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value.strip("# ").strip()


def _line_number_for_offset(text: str, offset: int) -> int:
    """Return a 1-based line number for a character offset."""
    if offset <= 0:
        return 1
    return text.count("\n", 0, min(offset, len(text))) + 1


def _citation_for_chunk(title: str, author: str | None, source_path: str, heading_path: str, start_line: int, end_line: int) -> str:
    author_part = f" — {author}" if author else ""
    heading_part = f" — {heading_path}" if heading_path else ""
    return f"{title}{author_part}{heading_part} — lines {start_line}-{end_line} — {source_path}"


def _chapter_from_stack(heading_stack: list[tuple[int, str]]) -> tuple[str, str]:
    if not heading_stack:
        return "body", "Body"

    # Prefer explicit book-like headings: Chapter 6, Preface, Introduction, etc.
    for _level, heading in heading_stack:
        clean = _clean_heading_title(heading)
        if CHAPTER_RE.match(clean):
            return slugify(clean), clean

    # Otherwise use the highest-level heading as the chapter-level container.
    top = _clean_heading_title(heading_stack[0][1])
    return slugify(top), top


def split_by_markdown_headings(text: str) -> list[dict[str, str | int]]:
    """Return heading-aware sections with stable chapter/section IDs and line ranges."""
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        stripped = text.strip()
        if not stripped:
            return []
        start_offset = text.find(stripped)
        end_offset = start_offset + len(stripped)
        return [
            {
                "heading_path": "",
                "section_text": stripped,
                "chapter_id": "body",
                "chapter_title": "Body",
                "section_id": "body",
                "section_title": "Body",
                "section_start_line": _line_number_for_offset(text, start_offset),
                "section_end_line": _line_number_for_offset(text, end_offset),
            }
        ]

    sections: list[dict[str, str | int]] = []
    heading_stack: list[tuple[int, str]] = []

    for idx, match in enumerate(matches):
        level = len(match.group(1))
        heading = _clean_heading_title(match.group(2))

        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()
        heading_stack.append((level, heading))

        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body_text = text[start:end].strip()
        heading_path = " > ".join(h for _, h in heading_stack)
        chapter_id, chapter_title = _chapter_from_stack(heading_stack)
        section_id = slugify(heading_path)

        if body_text:
            section_text = f"{match.group(0)}\n\n{body_text}"
            sections.append(
                {
                    "heading_path": heading_path,
                    "section_text": section_text,
                    "chapter_id": chapter_id,
                    "chapter_title": chapter_title,
                    "section_id": section_id,
                    "section_title": heading,
                    "section_start_line": _line_number_for_offset(text, match.start()),
                    "section_end_line": _line_number_for_offset(text, end),
                }
            )

    return sections


def split_large_section(
    section_text: str,
    target_chars: int,
    overlap_chars: int,
) -> list[tuple[str, int, int]]:
    """Split a section into chunks and return text plus section-relative char offsets."""
    if len(section_text) <= target_chars:
        return [(section_text, 0, len(section_text))]

    chunks: list[tuple[str, int, int]] = []
    start = 0

    while start < len(section_text):
        end = min(start + target_chars, len(section_text))
        raw_chunk = section_text[start:end]
        leading_trim = len(raw_chunk) - len(raw_chunk.lstrip())
        trailing_trim = len(raw_chunk.rstrip())
        chunk = raw_chunk.strip()
        if chunk:
            real_start = start + leading_trim
            real_end = start + trailing_trim
            chunks.append((chunk, real_start, real_end))
        if end >= len(section_text):
            break
        start = max(0, end - overlap_chars)

    return chunks


def chunk_markdown_file(
    path: Path,
    books_dir: Path,
    target_chars: int = 3500,
    overlap_chars: int = 500,
) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    meta, body = parse_frontmatter(raw)
    md = metadata_from_frontmatter(path, books_dir, meta)

    book_id = slugify(f"{md['author'] or ''}_{md['title']}")
    sections = split_by_markdown_headings(body)

    chunks: list[Chunk] = []
    chunk_index = 0

    for section in sections:
        section_text = str(section["section_text"])
        section_start_line = int(section.get("section_start_line", 1))
        for piece, rel_start, rel_end in split_large_section(section_text, target_chars, overlap_chars):
            hash_value = content_hash(piece)
            chunk_id = f"{book_id}::chunk_{chunk_index:06d}"
            start_line = section_start_line + piece.count("\n", 0, 0) + section_text.count("\n", 0, rel_start)
            end_line = section_start_line + section_text.count("\n", 0, rel_end)
            heading_path = str(section["heading_path"])
            citation = _citation_for_chunk(md["title"], md["author"], str(path), heading_path, start_line, end_line)
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    book_id=book_id,
                    title=md["title"],
                    author=md["author"],
                    source_path=str(path),
                    heading_path=section["heading_path"],
                    chapter_id=section["chapter_id"],
                    chapter_title=section["chapter_title"],
                    section_id=str(section["section_id"]),
                    section_title=str(section["section_title"]),
                    start_line=start_line,
                    end_line=end_line,
                    citation=citation,
                    chunk_index=chunk_index,
                    previous_chunk_id=None,
                    next_chunk_id=None,
                    text=piece,
                    char_count=len(piece),
                    content_hash=hash_value,
                    primary_class=md["primary_class"],
                    primary_class_label=md["primary_class_label"],
                    secondary_class_text=md["secondary_class_text"],
                    routing_aliases_text=md["routing_aliases_text"],
                    topics_text=md["topics_text"],
                )
            )
            chunk_index += 1

    for idx, chunk in enumerate(chunks):
        chunk.previous_chunk_id = chunks[idx - 1].chunk_id if idx > 0 else None
        chunk.next_chunk_id = chunks[idx + 1].chunk_id if idx < len(chunks) - 1 else None

    return chunks
