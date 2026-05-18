"""Structured evidence packs for answering from the BookMem corpus."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from .router import route_query
from .search import search_books, read_around, format_markdown_citation
from .summaries import search_summaries
from .book_graph import related_books, build_book_graph
from .config import get_settings


ANSWER_PACK_VERSION = "0.1.0"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _route_to_dict(route: Any) -> dict[str, Any]:
    if hasattr(route, "model_dump"):
        return route.model_dump()
    if hasattr(route, "__dict__"):
        return dict(route.__dict__)
    if isinstance(route, dict):
        return route
    return {"route": str(route)}


def _normalise_row(row: dict[str, Any], include_text: bool = True, excerpt_chars: int = 700) -> dict[str, Any]:
    text = (row.get("text") or "").strip()
    payload = {
        "chunk_id": row.get("chunk_id"),
        "book_id": row.get("book_id"),
        "title": row.get("title"),
        "author": row.get("author"),
        "primary_class": row.get("primary_class"),
        "primary_label": row.get("primary_label"),
        "chapter_id": row.get("chapter_id"),
        "chapter_title": row.get("chapter_title"),
        "section_id": row.get("section_id"),
        "section_title": row.get("section_title"),
        "heading_path": row.get("heading_path"),
        "start_line": row.get("start_line"),
        "end_line": row.get("end_line"),
        "source_path": row.get("source_path"),
        "citation": row.get("citation") or format_markdown_citation(row),
        "previous_chunk_id": row.get("previous_chunk_id"),
        "next_chunk_id": row.get("next_chunk_id"),
    }
    if include_text:
        payload["text"] = text
    else:
        payload["excerpt"] = text[:excerpt_chars].rstrip() + ("..." if len(text) > excerpt_chars else "")
    return payload


def _unique_books_from_passages(passages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    books = []
    for passage in passages:
        key = passage.get("book_id") or f"{passage.get('title')}::{passage.get('author')}"
        if key in seen:
            continue
        seen.add(str(key))
        books.append(
            {
                "book_id": passage.get("book_id"),
                "title": passage.get("title"),
                "author": passage.get("author"),
                "primary_class": passage.get("primary_class"),
                "primary_label": passage.get("primary_label"),
                "source_path": passage.get("source_path"),
            }
        )
    return books


def _suggested_synthesis(query: str, route: dict[str, Any], passages: list[dict[str, Any]], related: list[dict[str, Any]]) -> dict[str, Any]:
    aliases = route.get("aliases") or []
    class_codes = route.get("class_codes") or route.get("classes") or []
    themes = []

    for passage in passages:
        for field in ("section_title", "chapter_title", "heading_path", "primary_label"):
            value = passage.get(field)
            if value and str(value) not in themes:
                themes.append(str(value))

    related_titles = []
    for item in related:
        node = item.get("node") or {}
        title = node.get("title")
        if title and title not in related_titles:
            related_titles.append(title)

    return {
        "stance": "evidence_pack_only",
        "note": "This is not a final answer. It is a structured evidence bundle for an agent or human to synthesise.",
        "likely_route": {
            "aliases": aliases,
            "class_codes": class_codes,
            "confidence": route.get("confidence"),
            "reason": route.get("reason"),
        },
        "possible_synthesis_points": [
            f"Start by answering the query directly: {query}",
            "Compare the strongest passages before generalising.",
            "Use the cited line ranges for claims.",
            "Mention disagreement or weak evidence if the retrieved passages are thin.",
        ],
        "recurring_themes": themes[:12],
        "related_books_to_consider": related_titles[:8],
    }


def build_answer_pack(
    query: str,
    limit: int = 6,
    context: int = 1,
    summaries_first: bool = True,
    include_text: bool = True,
    rebuild_graph: bool = False,
) -> dict[str, Any]:
    route_obj = route_query(query)
    route = _route_to_dict(route_obj)

    aliases = route.get("aliases") or []
    class_codes = route.get("class_codes") or []
    alias = aliases[0] if aliases else None

    top_passage_rows: list[dict[str, Any]] = []
    search_errors: list[str] = []

    # Prefer routed search, then fallback to broad search.
    try:
        if class_codes:
            for class_code in class_codes[:3]:
                top_passage_rows.extend(search_books(query=query, limit=max(1, limit), class_code=[str(class_code)]))
                if len(top_passage_rows) >= limit:
                    break
        elif alias:
            top_passage_rows.extend(search_books(query=query, limit=limit, alias=[str(alias)]))
    except Exception as exc:
        search_errors.append(f"routed search failed: {exc}")

    if len(top_passage_rows) < limit:
        try:
            fallback_rows = search_books(query=query, limit=limit)
            seen = {row.get("chunk_id") for row in top_passage_rows}
            for row in fallback_rows:
                if row.get("chunk_id") not in seen:
                    top_passage_rows.append(row)
                if len(top_passage_rows) >= limit:
                    break
        except Exception as exc:
            search_errors.append(f"fallback search failed: {exc}")

    top_passage_rows = top_passage_rows[:limit]
    top_passages = [_normalise_row(row, include_text=include_text) for row in top_passage_rows]

    context_blocks = []
    for passage in top_passages:
        chunk_id = passage.get("chunk_id")
        if not chunk_id:
            continue
        try:
            rows = read_around(chunk_id=chunk_id, before=context, after=context)
            context_blocks.append(
                {
                    "anchor_chunk_id": chunk_id,
                    "anchor_citation": passage.get("citation"),
                    "chunks": [_normalise_row(row, include_text=include_text) for row in rows],
                }
            )
        except Exception as exc:
            context_blocks.append(
                {
                    "anchor_chunk_id": chunk_id,
                    "anchor_citation": passage.get("citation"),
                    "error": str(exc),
                    "chunks": [],
                }
            )

    summary_matches = []
    if summaries_first:
        try:
            summary_matches = search_summaries(query, limit=limit)
        except Exception as exc:
            search_errors.append(f"summary search failed: {exc}")

    graph_path = Path("data/graphs/book_graph.json")
    related_result = {"related": []}
    try:
        if rebuild_graph or not graph_path.exists():
            build_book_graph(output_path=graph_path)
        related_result = related_books(topic=query, limit=limit, graph_path=graph_path)
    except Exception as exc:
        search_errors.append(f"related graph lookup failed: {exc}")

    citations = []
    seen_citations = set()
    for passage in top_passages:
        citation = passage.get("citation")
        if citation and citation not in seen_citations:
            citations.append(citation)
            seen_citations.add(citation)
    for block in context_blocks:
        for chunk in block.get("chunks", []):
            citation = chunk.get("citation")
            if citation and citation not in seen_citations:
                citations.append(citation)
                seen_citations.add(citation)

    relevant_books = _unique_books_from_passages(top_passages)
    synthesis = _suggested_synthesis(query, route, top_passages, related_result.get("related", []))

    return {
        "schema_version": 1,
        "answer_pack_version": ANSWER_PACK_VERSION,
        "created_at": utc_now_iso(),
        "query": query,
        "route": route,
        "relevant_books": relevant_books,
        "summary_matches": summary_matches,
        "top_passages": top_passages,
        "read_around_context": context_blocks,
        "related_books": related_result.get("related", []),
        "suggested_synthesis": synthesis,
        "citations": citations,
        "errors": search_errors,
    }
