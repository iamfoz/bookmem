"""Local HTTP API for BookMem.

This service is intended for local/container integration. It exposes a
small FastAPI surface over the same search, routing, reading and metadata
functions used by the CLI and MCP server.
"""

from __future__ import annotations

from typing import Any, Literal
import os

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

from . import __version__
from .config import get_settings
from .frontmatter import discover_book_files, read_frontmatter_and_body
from .router import route_query
from .search import (
    read_around,
    read_chapter,
    read_chunk,
    read_section,
    search_books,
)
from .topic_maps import build_topic_map



def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def api_auth_required() -> bool:
    return _truthy(os.getenv("BOOKMEM_API_REQUIRE_KEY"))


def configured_api_key() -> str | None:
    value = os.getenv("BOOKMEM_API_KEY")
    if value is None:
        return None
    value = value.strip()
    return value or None


def require_api_key(request: Request) -> None:
    """Require Authorization: Bearer <token> when API auth is enabled."""
    if not api_auth_required():
        return

    expected = configured_api_key()
    if not expected:
        raise HTTPException(
            status_code=500,
            detail="BOOKMEM_API_REQUIRE_KEY is enabled but BOOKMEM_API_KEY is not set.",
        )

    header = request.headers.get("authorization", "")
    prefix = "Bearer "
    if not header.startswith(prefix):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    supplied = header[len(prefix):].strip()
    if supplied != expected:
        raise HTTPException(status_code=403, detail="Invalid bearer token.")


app = FastAPI(
    title="BookMem API",
    version=__version__,
    description="Local HTTP API for the BookMem Markdown book corpus.",
)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=8, ge=1, le=50)
    book: str | None = None
    aliases: list[str] = Field(default_factory=list)
    class_codes: list[str] = Field(default_factory=list)
    mode: Literal["hybrid", "vector", "fts"] = "hybrid"
    include_text: bool = False


class RouteRequest(BaseModel):
    query: str = Field(..., min_length=1)


class TopicMapRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    book_limit: int = Field(default=8, ge=1, le=25)
    summary_limit: int = Field(default=20, ge=1, le=100)
    chunk_limit: int = Field(default=20, ge=1, le=100)
    include_chunks: bool = True


def _public_chunk(row: dict[str, Any], include_text: bool = True) -> dict[str, Any]:
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

    text = row.get("text", "") or ""
    if include_text:
        payload["text"] = text
    else:
        payload["excerpt"] = text[:900].strip() + ("..." if len(text) > 900 else "")

    return payload


def _book_from_frontmatter(path) -> dict[str, Any]:
    fm, _body = read_frontmatter_and_body(path)
    classification = fm.get("classification", {}) or {}
    return {
        "book_id": fm.get("book_id"),
        "title": fm.get("title"),
        "author": fm.get("author"),
        "isbn": fm.get("isbn"),
        "primary_class": classification.get("primary_class"),
        "primary_label": classification.get("primary_label"),
        "secondary_classes": classification.get("secondary_classes", []),
        "routing_aliases": classification.get("routing_aliases", []),
        "topics": classification.get("topics", []),
        "path": str(path),
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "api_auth_required": str(api_auth_required()).lower()}


@app.get("/books")
def list_books(
    auth: None = Depends(require_api_key),
    class_code: str | None = Query(default=None),
    author: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    settings = get_settings()
    books = []

    for path in discover_book_files(settings.books_dir):
        fm, _body = read_frontmatter_and_body(path)
        if not fm:
            continue

        book = _book_from_frontmatter(path)

        if class_code and str(book.get("primary_class")) != str(class_code):
            continue

        if author and author.lower() not in str(book.get("author") or "").lower():
            continue

        books.append(book)

    books.sort(key=lambda item: ((item.get("title") or "").lower(), (item.get("author") or "").lower()))
    return {"count": min(len(books), limit), "books": books[:limit]}


@app.post("/search")
def search(request: SearchRequest, auth: None = Depends(require_api_key)) -> dict[str, Any]:
    results = search_books(
        query=request.query,
        limit=request.limit,
        book=request.book,
        class_code=request.class_codes or None,
        alias=request.aliases or None,
        mode=request.mode,
    )
    return {
        "query": request.query,
        "limit": request.limit,
        "book": request.book,
        "aliases": request.aliases,
        "class_codes": request.class_codes,
        "mode": request.mode,
        "results": [_public_chunk(row, include_text=request.include_text) for row in results],
    }


@app.post("/route")
def route(request: RouteRequest, auth: None = Depends(require_api_key)) -> dict[str, Any]:
    routed = route_query(request.query)
    if hasattr(routed, "model_dump"):
        return routed.model_dump()
    if hasattr(routed, "__dict__"):
        return dict(routed.__dict__)
    return {"query": request.query, "route": routed}


@app.get("/chunks/{chunk_id}")
def get_chunk(
    chunk_id: str,
    context: int = Query(default=0, ge=0, le=20),
    auth: None = Depends(require_api_key),
) -> dict[str, Any]:
    chunks = read_chunk(chunk_id=chunk_id, context=context)
    if not chunks:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return {
        "chunk_id": chunk_id,
        "context": context,
        "chunks": [_public_chunk(row, include_text=True) for row in chunks],
    }


@app.get("/chunks/{chunk_id}/around")
def get_chunk_around(
    chunk_id: str,
    before: int = Query(default=2, ge=0, le=20),
    after: int = Query(default=3, ge=0, le=20),
    auth: None = Depends(require_api_key),
) -> dict[str, Any]:
    chunks = read_around(chunk_id=chunk_id, before=before, after=after)
    if not chunks:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return {
        "chunk_id": chunk_id,
        "before": before,
        "after": after,
        "chunks": [_public_chunk(row, include_text=True) for row in chunks],
    }


@app.get("/chunks/{chunk_id}/section")
def get_chunk_section(chunk_id: str, auth: None = Depends(require_api_key)) -> dict[str, Any]:
    chunks = read_section(chunk_id=chunk_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="Chunk or section not found")
    return {"chunk_id": chunk_id, "chunks": [_public_chunk(row, include_text=True) for row in chunks]}


@app.get("/books/{book_id}/chapters")
def list_book_chapters(book_id: str, auth: None = Depends(require_api_key)) -> dict[str, Any]:
    # Reuse indexed rows for chapter discovery.
    from .search import _rows_for_book  # local import keeps internal helper private elsewhere

    rows = _rows_for_book(book_id)
    if rows.empty:
        raise HTTPException(status_code=404, detail="Book not found in index")

    chapters = []
    seen = set()
    for _idx, row in rows.sort_values("chunk_index").iterrows():
        chapter_id = row.get("chapter_id")
        if not chapter_id or chapter_id in seen:
            continue
        seen.add(chapter_id)
        chapters.append(
            {
                "chapter_id": chapter_id,
                "chapter_title": row.get("chapter_title"),
                "first_chunk_id": row.get("chunk_id"),
                "start_line": row.get("start_line"),
            }
        )

    return {"book_id": book_id, "count": len(chapters), "chapters": chapters}


@app.get("/books/{book_id}/chapters/{chapter}")
def get_book_chapter(book_id: str, chapter: str, auth: None = Depends(require_api_key)) -> dict[str, Any]:
    chunks = read_chapter(book=book_id, chapter=chapter)
    if not chunks:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return {
        "book_id": book_id,
        "chapter": chapter,
        "chunks": [_public_chunk(row, include_text=True) for row in chunks],
    }


@app.post("/topic-map")
def topic_map(request: TopicMapRequest, auth: None = Depends(require_api_key)) -> dict[str, Any]:
    result = build_topic_map(
        topic=request.topic,
        book_limit=request.book_limit,
        summary_limit=request.summary_limit,
        chunk_limit=request.chunk_limit,
        include_chunks=request.include_chunks,
    )
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    return {"topic": request.topic, "result": result}
