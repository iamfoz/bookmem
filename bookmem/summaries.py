from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import math
import re
from typing import Any

import yaml

from .chunking import parse_frontmatter, slugify, split_by_markdown_headings
from .config import get_settings
from .embeddings import embed_texts
from .manifest import get_record_for_path, upsert_book_record, relative_or_absolute, markdown_hashes
from .taxonomy import get_class_label, infer_class_from_path, normalise_alias

SUMMARY_SCHEMA_VERSION = 1
SUMMARY_GENERATOR_VERSION = "0.1.0"

STOPWORDS = {
    "the", "and", "for", "that", "with", "this", "from", "into", "your", "you", "are",
    "was", "were", "have", "has", "had", "not", "but", "can", "will", "what", "when",
    "where", "why", "how", "book", "chapter", "introduction", "preface", "edition",
    "about", "after", "before", "because", "between", "through", "there", "their", "them",
    "they", "then", "than", "also", "more", "most", "some", "such", "over", "under",
    "still", "almost", "everything", "second", "first", "one", "two", "three", "four",
}


@dataclass
class SummaryResult:
    book_id: str
    title: str
    author: str | None
    summary_dir: Path
    book_summary_path: Path
    chapter_summary_path: Path
    chapter_count: int
    written: bool


@dataclass
class SummarySearchResult:
    score: float
    level: str
    book_id: str
    title: str
    author: str | None
    summary_path: Path
    chapter_title: str | None
    text: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def summaries_root() -> Path:
    settings = get_settings()
    explicit = getattr(settings, "summaries_dir", None)
    if explicit:
        return explicit
    return settings.books_dir.parent / "summaries"


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


def _book_metadata(path: Path, meta: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    title = str(meta.get("title") or path.stem).strip()
    author = meta.get("author")
    author = str(author).strip() if author else None

    classification = meta.get("classification") if isinstance(meta.get("classification"), dict) else {}
    inferred_class, inferred_label = infer_class_from_path(path, settings.books_dir)
    primary_class = str(classification.get("primary_class") or meta.get("primary_class") or inferred_class)
    primary_label = str(
        classification.get("primary_label")
        or meta.get("primary_class_label")
        or get_class_label(primary_class)
        or inferred_label
    )

    topics = _normalise_list(classification.get("topics") or meta.get("topics"))
    aliases = _normalise_list(classification.get("routing_aliases") or meta.get("routing_aliases"))
    secondary = _normalise_list(classification.get("secondary_class") or meta.get("secondary_class"))

    book_id = slugify(f"{author or ''}_{title}")
    return {
        "book_id": book_id,
        "title": title,
        "author": author,
        "primary_class": primary_class,
        "primary_label": primary_label,
        "secondary_classes": secondary,
        "routing_aliases": aliases,
        "topics": topics,
    }


def _strip_markdown(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_~>#]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _first_substantial_paragraph(text: str, max_chars: int = 700) -> str:
    for para in re.split(r"\n\s*\n", text):
        cleaned = _strip_markdown(para)
        if len(cleaned) >= 120 and not cleaned.lower().startswith(("copyright", "all rights reserved")):
            return cleaned[:max_chars].rstrip()
    cleaned = _strip_markdown(text)
    return cleaned[:max_chars].rstrip()


def _keyword_candidates(text: str, limit: int = 18) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z\-']{3,}", text.lower())
    counts: dict[str, int] = {}
    for word in words:
        word = word.strip("-' ")
        if not word or word in STOPWORDS or len(word) < 4:
            continue
        counts[word] = counts.get(word, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, _count in ranked[:limit]]


def _heading_ideas(sections: list[tuple[str, str]], topics: list[str], limit: int = 10) -> list[str]:
    ideas: list[str] = []
    seen: set[str] = set()

    for item in topics:
        key = normalise_alias(item)
        if key and key not in seen:
            ideas.append(item)
            seen.add(key)

    for heading_path, _text in sections:
        parts = [part.strip() for part in heading_path.split(">") if part.strip()]
        for part in parts[-2:]:
            cleaned = re.sub(r"^chapter\s+\d+\s*[:.-]?\s*", "", part, flags=re.I).strip()
            if not cleaned or len(cleaned) < 4:
                continue
            key = normalise_alias(cleaned)
            if key not in seen:
                ideas.append(cleaned)
                seen.add(key)
            if len(ideas) >= limit:
                return ideas
    return ideas[:limit]


def _best_for(meta: dict[str, Any], ideas: list[str], text: str, limit: int = 8) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for source in (meta.get("routing_aliases") or [], meta.get("topics") or [], ideas):
        for item in source:
            cleaned = str(item).replace("_", " ").strip()
            key = normalise_alias(cleaned)
            if key and key not in seen:
                values.append(cleaned)
                seen.add(key)
            if len(values) >= limit:
                return values
    for keyword in _keyword_candidates(text, limit=limit):
        key = normalise_alias(keyword)
        if key not in seen:
            values.append(keyword)
            seen.add(key)
        if len(values) >= limit:
            break
    return values


def _chapter_key(heading_path: str) -> str:
    if not heading_path:
        return "Unheaded content"
    parts = [part.strip() for part in heading_path.split(">") if part.strip()]
    return parts[0] if parts else "Unheaded content"


def _chapter_sort_key(title: str) -> tuple[int, str]:
    match = re.search(r"chapter\s+(\d+)", title, flags=re.I)
    if match:
        return (int(match.group(1)), title.lower())
    special = {"preface": -30, "introduction": -20, "prologue": -10, "conclusion": 10_000}
    return (special.get(title.lower(), 5_000), title.lower())


def _chapter_summaries(sections: list[tuple[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[tuple[str, str]]] = {}
    for heading_path, section_text in sections:
        grouped.setdefault(_chapter_key(heading_path), []).append((heading_path, section_text))

    chapters: list[dict[str, Any]] = []
    for chapter_title in sorted(grouped, key=_chapter_sort_key):
        items = grouped[chapter_title]
        combined = "\n\n".join(text for _heading, text in items)
        headings = []
        for heading_path, _text in items:
            parts = [part.strip() for part in heading_path.split(">") if part.strip()]
            if len(parts) > 1:
                headings.append(parts[-1])
        ideas = _heading_ideas(items, [], limit=8)
        chapters.append(
            {
                "chapter_id": slugify(chapter_title),
                "title": chapter_title,
                "summary": _first_substantial_paragraph(combined, max_chars=550),
                "major_ideas": ideas,
                "headings": list(dict.fromkeys(headings))[:20],
                "keywords": _keyword_candidates(combined, limit=12),
                "source_section_count": len(items),
                "source_char_count": len(combined),
            }
        )
    return chapters


def summarise_book(path: Path, write: bool = True, overwrite: bool = True) -> SummaryResult:
    raw = path.read_text(encoding="utf-8", errors="replace")
    meta, body = parse_frontmatter(raw)
    book_meta = _book_metadata(path, meta)
    sections = split_by_markdown_headings(body)
    combined_text = "\n\n".join(section_text for _heading, section_text in sections) or body

    ideas = _heading_ideas(sections, book_meta["topics"], limit=12)
    best_for = _best_for(book_meta, ideas, combined_text, limit=10)

    book_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "generator_version": SUMMARY_GENERATOR_VERSION,
        "generated_at": utc_now_iso(),
        "book_id": book_meta["book_id"],
        "title": book_meta["title"],
        "author": book_meta["author"],
        "source_path": relative_or_absolute(path),
        "classification": {
            "scheme": "BMDC",
            "primary_class": book_meta["primary_class"],
            "primary_label": book_meta["primary_label"],
            "secondary_classes": book_meta["secondary_classes"],
            "routing_aliases": book_meta["routing_aliases"],
            "topics": book_meta["topics"],
        },
        "core_thesis": _first_substantial_paragraph(combined_text, max_chars=750),
        "major_ideas": ideas,
        "best_for_questions_about": best_for,
        "keywords": _keyword_candidates(combined_text, limit=20),
        "chapter_count": 0,
        "summary_kind": "deterministic_extract",
        "review_status": "machine_draft",
    }

    chapters = _chapter_summaries(sections)
    book_summary["chapter_count"] = len(chapters)
    chapter_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "generator_version": SUMMARY_GENERATOR_VERSION,
        "generated_at": book_summary["generated_at"],
        "book_id": book_meta["book_id"],
        "title": book_meta["title"],
        "author": book_meta["author"],
        "source_path": relative_or_absolute(path),
        "chapters": chapters,
    }

    out_dir = summaries_root() / book_meta["book_id"]
    book_path = out_dir / "book.yaml"
    chapters_path = out_dir / "chapters.yaml"
    written = False

    if write:
        out_dir.mkdir(parents=True, exist_ok=True)
        if overwrite or not book_path.exists():
            book_path.write_text(yaml.safe_dump(book_summary, sort_keys=False, allow_unicode=True), encoding="utf-8")
        if overwrite or not chapters_path.exists():
            chapters_path.write_text(yaml.safe_dump(chapter_summary, sort_keys=False, allow_unicode=True), encoding="utf-8")
        written = True

        content_hash, frontmatter_hash, full_hash = markdown_hashes(path)
        existing = get_record_for_path(path) or {}
        upsert_book_record(
            {
                **existing,
                "book_id": book_meta["book_id"],
                "canonical_path": relative_or_absolute(path),
                "content_hash": content_hash,
                "frontmatter_hash": frontmatter_hash,
                "full_hash": full_hash,
                "last_summarised": book_summary["generated_at"],
                "summary_path": relative_or_absolute(book_path),
                "chapter_summary_path": relative_or_absolute(chapters_path),
                "summary_generator_version": SUMMARY_GENERATOR_VERSION,
                "chapter_count": len(chapters),
            }
        )

    return SummaryResult(
        book_id=book_meta["book_id"],
        title=book_meta["title"],
        author=book_meta["author"],
        summary_dir=out_dir,
        book_summary_path=book_path,
        chapter_summary_path=chapters_path,
        chapter_count=len(chapters),
        written=written,
    )


def summarise_books(root: Path, write: bool = True, overwrite: bool = True) -> list[SummaryResult]:
    files = sorted(root.glob("**/*.md"))
    return [summarise_book(path, write=write, overwrite=overwrite) for path in files]


def _summary_text_from_book_yaml(data: dict[str, Any]) -> str:
    parts = [
        str(data.get("title") or ""),
        str(data.get("author") or ""),
        str(data.get("core_thesis") or ""),
        " ".join(_normalise_list(data.get("major_ideas"))),
        " ".join(_normalise_list(data.get("best_for_questions_about"))),
        " ".join(_normalise_list(data.get("keywords"))),
    ]
    classification = data.get("classification") if isinstance(data.get("classification"), dict) else {}
    parts.extend(
        [
            str(classification.get("primary_class") or ""),
            str(classification.get("primary_label") or ""),
            " ".join(_normalise_list(classification.get("topics"))),
            " ".join(_normalise_list(classification.get("routing_aliases"))),
        ]
    )
    return "\n".join(part for part in parts if part)


def _summary_docs(root: Path | None = None, include_chapters: bool = True) -> list[SummarySearchResult]:
    base = root or summaries_root()
    docs: list[SummarySearchResult] = []
    if not base.exists():
        return docs

    for book_yaml in sorted(base.glob("*/book.yaml")):
        data = yaml.safe_load(book_yaml.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            continue
        docs.append(
            SummarySearchResult(
                score=0.0,
                level="book",
                book_id=str(data.get("book_id") or book_yaml.parent.name),
                title=str(data.get("title") or book_yaml.parent.name),
                author=data.get("author"),
                summary_path=book_yaml,
                chapter_title=None,
                text=_summary_text_from_book_yaml(data),
            )
        )

        chapters_yaml = book_yaml.parent / "chapters.yaml"
        if include_chapters and chapters_yaml.exists():
            chapter_data = yaml.safe_load(chapters_yaml.read_text(encoding="utf-8")) or {}
            if isinstance(chapter_data, dict):
                for chapter in chapter_data.get("chapters", []) or []:
                    if not isinstance(chapter, dict):
                        continue
                    text = "\n".join(
                        [
                            str(chapter_data.get("title") or ""),
                            str(chapter.get("title") or ""),
                            str(chapter.get("summary") or ""),
                            " ".join(_normalise_list(chapter.get("major_ideas"))),
                            " ".join(_normalise_list(chapter.get("headings"))),
                            " ".join(_normalise_list(chapter.get("keywords"))),
                        ]
                    )
                    docs.append(
                        SummarySearchResult(
                            score=0.0,
                            level="chapter",
                            book_id=str(chapter_data.get("book_id") or book_yaml.parent.name),
                            title=str(chapter_data.get("title") or book_yaml.parent.name),
                            author=chapter_data.get("author"),
                            summary_path=chapters_yaml,
                            chapter_title=str(chapter.get("title") or ""),
                            text=text,
                        )
                    )
    return docs


def search_summaries(query: str, limit: int = 8, include_chapters: bool = True, root: Path | None = None) -> list[SummarySearchResult]:
    docs = _summary_docs(root=root, include_chapters=include_chapters)
    if not docs:
        return []

    texts = [query] + [doc.text for doc in docs]
    vectors = embed_texts(texts)
    qv = vectors[0]
    scored: list[SummarySearchResult] = []
    for doc, vec in zip(docs, vectors[1:]):
        score = sum(float(a) * float(b) for a, b in zip(qv, vec))
        if math.isnan(score):
            score = 0.0
        scored.append(
            SummarySearchResult(
                score=score,
                level=doc.level,
                book_id=doc.book_id,
                title=doc.title,
                author=doc.author,
                summary_path=doc.summary_path,
                chapter_title=doc.chapter_title,
                text=doc.text,
            )
        )
    return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]
