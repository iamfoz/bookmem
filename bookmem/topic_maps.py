from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import re
from typing import Any

import yaml

from .router import route_query
from .search import format_markdown_citation, search_books
from .summaries import search_summaries
from .taxonomy import normalise_alias

TOPIC_MAP_VERSION = "0.1.0"

STOPWORDS = {
    "about", "after", "again", "against", "also", "almost", "among", "another",
    "because", "before", "being", "between", "book", "books", "chapter", "could",
    "does", "during", "each", "either", "every", "from", "have", "into", "more",
    "most", "other", "over", "should", "still", "summary", "than", "that", "their",
    "them", "there", "these", "they", "this", "through", "title", "under", "using",
    "what", "when", "where", "which", "while", "with", "would", "your",
}

PHRASE_PATTERNS = [
    r"\b[a-z][a-z]+\s+versus\s+[a-z][a-z]+\b",
    r"\b[a-z][a-z]+\s+vs\.?\s+[a-z][a-z]+\b",
    r"\b[a-z][a-z]+\s+over\s+[a-z][a-z]+\b",
    r"\b[a-z][a-z]+\s+and\s+[a-z][a-z]+\b",
    r"\b[a-z][a-z]+\s+of\s+[a-z][a-z]+\b",
    r"\b[a-z][a-z]+\s+[a-z][a-z]+\b",
]


@dataclass
class TopicMapBook:
    title: str
    author: str | None
    book_id: str
    score: float
    reasons: list[str] = field(default_factory=list)
    summary_hits: list[dict[str, Any]] = field(default_factory=list)
    chunk_hits: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TopicMap:
    query: str
    route: dict[str, Any]
    strongest_books: list[TopicMapBook]
    common_themes: list[str]
    summary_hit_count: int
    chunk_hit_count: int
    topic_map_version: str = TOPIC_MAP_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "route": self.route,
            "strongest_books": [
                {
                    "rank": idx,
                    "title": book.title,
                    "author": book.author,
                    "book_id": book.book_id,
                    "score": round(book.score, 4),
                    "reasons": book.reasons,
                    "summary_hits": book.summary_hits,
                    "chunk_hits": book.chunk_hits,
                }
                for idx, book in enumerate(self.strongest_books, start=1)
            ],
            "common_themes": self.common_themes,
            "summary_hit_count": self.summary_hit_count,
            "chunk_hit_count": self.chunk_hit_count,
            "topic_map_version": self.topic_map_version,
        }

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def _strip_markdown(value: str) -> str:
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"[*_~>#{}\[\]()]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _phrase_candidates(text: str, query: str, limit: int = 16) -> list[str]:
    text_norm = _strip_markdown(text).lower()
    query_terms = {
        token
        for token in re.findall(r"[a-z][a-z0-9\-]{2,}", query.lower())
        if token not in STOPWORDS
    }
    counts: dict[str, float] = {}

    for pattern in PHRASE_PATTERNS:
        for match in re.findall(pattern, text_norm):
            phrase = re.sub(r"\s+", " ", match).strip(" -.,:;")
            if len(phrase) < 6:
                continue
            words = [w for w in phrase.split() if w not in STOPWORDS]
            if not words:
                continue
            score = 1.0 + (0.75 * len(query_terms.intersection(words)))
            if any(word in phrase for word in ("chapter", "summary", "unknown")):
                continue
            counts[phrase] = counts.get(phrase, 0.0) + score

    # Single strong keyword fallback.
    words = [
        word.strip("-' ")
        for word in re.findall(r"[a-z][a-z\-']{3,}", text_norm)
    ]
    for word in words:
        if word and word not in STOPWORDS:
            counts[word] = counts.get(word, 0.0) + (1.3 if word in query_terms else 0.3)

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    themes: list[str] = []
    seen: set[str] = set()
    for phrase, _score in ranked:
        key = normalise_alias(phrase)
        if not key or key in seen:
            continue
        # Avoid very generic one-word themes unless they were query terms.
        if " " not in phrase and phrase not in query_terms and len(themes) >= 6:
            continue
        themes.append(phrase)
        seen.add(key)
        if len(themes) >= limit:
            break
    return themes


def _summary_excerpt(text: str, max_chars: int = 500) -> str:
    cleaned = _strip_markdown(text)
    return cleaned[:max_chars].rstrip() + ("..." if len(cleaned) > max_chars else "")


def _add_reason(reasons: list[str], reason: str) -> None:
    reason = reason.strip()
    if reason and reason not in reasons:
        reasons.append(reason)


def map_topic(
    query: str,
    *,
    book_limit: int = 8,
    summary_limit: int = 12,
    chunk_limit: int = 12,
    themes_limit: int = 12,
    include_chunks: bool = True,
    fallback: bool = True,
) -> TopicMap:
    """Build a topic map from summary hits and optional chunk hits."""
    route = route_query(query)
    books: dict[str, TopicMapBook] = {}
    corpus_text_parts: list[str] = [query]

    summary_results = search_summaries(query=query, limit=summary_limit, include_chapters=True)
    for result in summary_results:
        book = books.setdefault(
            result.book_id,
            TopicMapBook(
                title=result.title,
                author=result.author,
                book_id=result.book_id,
                score=0.0,
            ),
        )
        summary_score = max(0.0, float(result.score))
        book.score += summary_score * (1.25 if result.level == "book" else 1.0)
        _add_reason(book.reasons, f"matched {result.level} summary")
        if result.chapter_title:
            _add_reason(book.reasons, f"chapter match: {result.chapter_title}")
        book.summary_hits.append(
            {
                "level": result.level,
                "score": round(summary_score, 4),
                "chapter_title": result.chapter_title,
                "summary_path": str(result.summary_path),
                "excerpt": _summary_excerpt(result.text),
            }
        )
        corpus_text_parts.append(result.text)

    chunk_results: list[dict[str, Any]] = []
    if include_chunks:
        try:
            chunk_results = search_books(
                query=query,
                limit=chunk_limit,
                class_code=route.class_codes or None,
                alias=route.aliases or None,
                mode="hybrid",
            )
            if not chunk_results and fallback and (route.class_codes or route.aliases):
                chunk_results = search_books(query=query, limit=chunk_limit, mode="hybrid")
        except Exception:
            chunk_results = []

    for row in chunk_results:
        book_id = str(row.get("book_id") or "unknown")
        title = str(row.get("title") or book_id)
        author = row.get("author")
        book = books.setdefault(
            book_id,
            TopicMapBook(title=title, author=author, book_id=book_id, score=0.0),
        )
        # LanceDB scores can be distance-like depending on mode/version, so avoid trusting them too much.
        book.score += 0.75
        _add_reason(book.reasons, "matched indexed chunks")
        heading = row.get("heading_path") or row.get("chapter_title") or ""
        if heading:
            _add_reason(book.reasons, f"chunk heading: {heading}")
        text = str(row.get("text") or "")
        corpus_text_parts.append(text)
        book.chunk_hits.append(
            {
                "chunk_id": row.get("chunk_id"),
                "chapter_title": row.get("chapter_title"),
                "section_title": row.get("section_title"),
                "heading_path": heading,
                "start_line": row.get("start_line"),
                "end_line": row.get("end_line"),
                "citation": format_markdown_citation(row),
                "excerpt": _summary_excerpt(text, max_chars=450),
            }
        )

    strongest = sorted(books.values(), key=lambda item: (-item.score, item.title.lower()))[:book_limit]
    common_themes = _phrase_candidates("\n".join(corpus_text_parts), query=query, limit=themes_limit)

    return TopicMap(
        query=query,
        route=route.to_dict(),
        strongest_books=strongest,
        common_themes=common_themes,
        summary_hit_count=len(summary_results),
        chunk_hit_count=len(chunk_results),
    )


def write_topic_map(topic_map: TopicMap, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".json":
        output.write_text(topic_map.to_json(indent=2) + "\n", encoding="utf-8")
    else:
        output.write_text(yaml.safe_dump(topic_map.to_dict(), sort_keys=False, allow_unicode=True), encoding="utf-8")
    return output
