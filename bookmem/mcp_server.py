"""Model Context Protocol server for BookMem.

The MCP server exposes the BookMem corpus as tools that other agents can call
directly. It is intentionally a thin integration layer over the existing
search, routing, reading, summary and topic-map modules.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import __version__
from .router import route_query
from .search import (
    search_books,
    read_chunk,
    read_around,
    read_chapter,
    read_section,
    get_table,
)
from .topic_maps import build_topic_map
from .frontmatter import discover_book_files, read_frontmatter_and_body
from .config import get_settings


mcp = FastMCP("BookMem")


def _safe_limit(value: int | None, default: int = 8, maximum: int = 50) -> int:
    if value is None:
        return default
    try:
        value = int(value)
    except Exception:
        return default
    return max(1, min(value, maximum))


def _public_chunk(row: dict[str, Any], include_text: bool = True) -> dict[str, Any]:
    """Return an MCP-safe chunk payload."""
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
        "citation": row.get("citation"),
        "source_path": row.get("source_path"),
        "previous_chunk_id": row.get("previous_chunk_id"),
        "next_chunk_id": row.get("next_chunk_id"),
    }
    if include_text:
        payload["text"] = row.get("text", "")
    else:
        text = row.get("text", "")
        payload["excerpt"] = text[:900].strip() + ("..." if len(text) > 900 else "")
    return payload


@mcp.tool(name="bookmem.search")
def mcp_search(
    query: str,
    limit: int = 8,
    alias: str | None = None,
    class_code: str | None = None,
    mode: str = "hybrid",
    include_text: bool = False,
) -> dict[str, Any]:
    """Search indexed BookMem chunks.

    Use this first when looking for passages from the book corpus. Prefer
    class_code or alias filters when the topic is known.
    """
    results = search_books(
        query=query,
        limit=_safe_limit(limit),
        alias=alias,
        class_code=class_code,
        mode=mode,
    )
    return {
        "query": query,
        "limit": _safe_limit(limit),
        "alias": alias,
        "class_code": class_code,
        "mode": mode,
        "results": [_public_chunk(row, include_text=include_text) for row in results],
    }


@mcp.tool(name="bookmem.read_chunk")
def mcp_read_chunk(chunk_id: str, context: int = 1) -> dict[str, Any]:
    """Read a chunk and optional neighbouring context."""
    chunks = read_chunk(chunk_id=chunk_id, context=_safe_limit(context, default=1, maximum=10))
    return {
        "chunk_id": chunk_id,
        "context": context,
        "chunks": [_public_chunk(row, include_text=True) for row in chunks],
    }


@mcp.tool(name="bookmem.read_around")
def mcp_read_around(chunk_id: str, before: int = 2, after: int = 3) -> dict[str, Any]:
    """Read chunks before and after a known chunk ID."""
    chunks = read_around(
        chunk_id=chunk_id,
        before=_safe_limit(before, default=2, maximum=20),
        after=_safe_limit(after, default=3, maximum=20),
    )
    return {
        "chunk_id": chunk_id,
        "before": before,
        "after": after,
        "chunks": [_public_chunk(row, include_text=True) for row in chunks],
    }


@mcp.tool(name="bookmem.read_section")
def mcp_read_section(chunk_id: str) -> dict[str, Any]:
    """Read the section containing a known chunk."""
    chunks = read_section(chunk_id=chunk_id)
    return {
        "chunk_id": chunk_id,
        "chunks": [_public_chunk(row, include_text=True) for row in chunks],
    }


@mcp.tool(name="bookmem.read_chapter")
def mcp_read_chapter(book: str, chapter: str) -> dict[str, Any]:
    """Read a chapter by book ID/title and chapter ID/title."""
    chunks = read_chapter(book=book, chapter=chapter)
    return {
        "book": book,
        "chapter": chapter,
        "chunks": [_public_chunk(row, include_text=True) for row in chunks],
    }


@mcp.tool(name="bookmem.list_books")
def mcp_list_books(
    class_code: str | None = None,
    author: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """List canonical books known to BookMem from Markdown frontmatter."""
    settings = get_settings()
    books = []
    for path in discover_book_files(settings.books_dir):
        fm, _body = read_frontmatter_and_body(path)
        if not fm:
            continue

        classification = fm.get("classification", {}) or {}
        primary_class = classification.get("primary_class")

        if class_code and str(primary_class) != str(class_code):
            continue

        book_author = fm.get("author")
        if author and author.lower() not in str(book_author or "").lower():
            continue

        books.append(
            {
                "book_id": fm.get("book_id"),
                "title": fm.get("title"),
                "author": book_author,
                "isbn": fm.get("isbn"),
                "primary_class": primary_class,
                "primary_label": classification.get("primary_label"),
                "routing_aliases": classification.get("routing_aliases", []),
                "topics": classification.get("topics", []),
                "path": str(path),
            }
        )

    books = sorted(books, key=lambda b: ((b.get("title") or "").lower(), (b.get("author") or "").lower()))
    return {
        "count": len(books[: _safe_limit(limit, default=100, maximum=500)]),
        "books": books[: _safe_limit(limit, default=100, maximum=500)],
    }


@mcp.tool(name="bookmem.route_query")
def mcp_route_query(query: str) -> dict[str, Any]:
    """Route a natural language query to likely BookMem aliases/classes."""
    route = route_query(query)
    if hasattr(route, "model_dump"):
        return route.model_dump()
    if hasattr(route, "__dict__"):
        return dict(route.__dict__)
    return json.loads(json.dumps(route, default=str))


@mcp.tool(name="bookmem.map_topic")
def mcp_map_topic(
    topic: str,
    book_limit: int = 8,
    summary_limit: int = 20,
    chunk_limit: int = 20,
    include_chunks: bool = True,
) -> dict[str, Any]:
    """Build a topic map across summaries and indexed chunks."""
    topic_map = build_topic_map(
        topic=topic,
        book_limit=_safe_limit(book_limit, default=8, maximum=25),
        summary_limit=_safe_limit(summary_limit, default=20, maximum=100),
        chunk_limit=_safe_limit(chunk_limit, default=20, maximum=100),
        include_chunks=include_chunks,
    )
    if hasattr(topic_map, "model_dump"):
        return topic_map.model_dump()
    if isinstance(topic_map, dict):
        return topic_map
    return json.loads(json.dumps(topic_map, default=str))


@mcp.resource("bookmem://version")
def mcp_version() -> str:
    """Return BookMem version information."""
    return f"BookMem {__version__}"


def main() -> None:
    """Run the BookMem MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
