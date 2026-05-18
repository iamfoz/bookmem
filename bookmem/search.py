from __future__ import annotations

import re

import lancedb

from .config import get_settings
from .embeddings import embed_texts
from .taxonomy import resolve_alias


def get_table():
    settings = get_settings()
    db = lancedb.connect(str(settings.db_dir))
    return db.open_table(settings.table_name)


def _quote(value: str) -> str:
    return value.replace("'", "''")


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_") or "untitled"


def build_where_clause(
    book: str | None = None,
    class_code: list[str] | None = None,
    alias: list[str] | None = None,
) -> str | None:
    parts: list[str] = []

    if book:
        safe_book = _quote(book)
        parts.append(f"(title = '{safe_book}' OR book_id = '{safe_book}')")

    class_codes = set(class_code or [])
    for item in alias or []:
        resolved = resolve_alias(item)
        class_codes.update(resolved.get("primary_class", []))
        class_codes.update(resolved.get("secondary_class", []))

    if class_codes:
        class_parts = []
        for code in sorted(class_codes):
            safe_code = _quote(code)
            class_parts.append(f"primary_class = '{safe_code}'")
            class_parts.append(f"secondary_class_text LIKE '%{safe_code}%'")
        parts.append("(" + " OR ".join(class_parts) + ")")

    return " AND ".join(parts) if parts else None


def search_books(
    query: str,
    limit: int = 8,
    book: str | None = None,
    class_code: list[str] | None = None,
    alias: list[str] | None = None,
    mode: str = "hybrid",
):
    table = get_table()
    where_clause = build_where_clause(book=book, class_code=class_code, alias=alias)

    if mode == "vector":
        vector = embed_texts([query])[0]
        q = table.search(vector)
    elif mode == "fts":
        q = table.search(query, query_type="fts")
    else:
        q = table.search(query, query_type="hybrid", vector_column_name="vector")

    if where_clause:
        q = q.where(where_clause)

    return q.limit(limit).to_list()


def format_source_location(row: dict) -> str:
    """Return a compact human-readable source location for a chunk row."""
    title = row.get("title") or "Untitled"
    author = row.get("author") or "Unknown author"
    chapter = row.get("chapter_title") or ""
    section = row.get("section_title") or ""
    start_line = row.get("start_line")
    end_line = row.get("end_line")
    source_path = row.get("source_path") or ""

    location_bits = []
    if chapter:
        location_bits.append(str(chapter))
    if section and section != chapter:
        location_bits.append(str(section))
    if start_line and end_line:
        location_bits.append(f"lines {start_line}-{end_line}")

    location = " · ".join(location_bits)
    if location:
        return f"{title} — {author} — {location} — {source_path}"
    return f"{title} — {author} — {source_path}"


def format_markdown_citation(row: dict) -> str:
    """Return a stable markdown-friendly citation string for agent answers."""
    title = row.get("title") or "Untitled"
    author = row.get("author") or "Unknown author"
    heading = row.get("heading_path") or row.get("chapter_title") or ""
    start_line = row.get("start_line")
    end_line = row.get("end_line")
    chunk_id = row.get("chunk_id") or ""
    source_path = row.get("source_path") or ""

    parts = [f"*{title}*", str(author)]
    if heading:
        parts.append(str(heading))
    if start_line and end_line:
        parts.append(f"lines {start_line}-{end_line}")
    if chunk_id:
        parts.append(f"chunk `{chunk_id}`")
    if source_path:
        parts.append(str(source_path))
    return "; ".join(parts)


def _rows_for_book(book: str):
    table = get_table()
    rows = table.to_pandas()
    if rows.empty:
        return rows
    return rows[(rows["book_id"] == book) | (rows["title"] == book)]


def _normalise_rows(rows):
    if hasattr(rows, "sort_values"):
        rows = rows.sort_values(["book_id", "chunk_index"])
        return rows.to_dict(orient="records")
    return sorted(rows, key=lambda row: (row.get("book_id", ""), int(row.get("chunk_index", 0))))


def read_chunk(chunk_id: str, context: int = 1):
    return read_around(chunk_id=chunk_id, before=context, after=context)


def read_around(chunk_id: str, before: int = 2, after: int = 2):
    """Read a chunk plus a configurable number of neighbours either side."""
    table = get_table()
    rows = table.to_pandas()
    if rows.empty:
        return []

    matches = rows[rows["chunk_id"] == chunk_id]
    if matches.empty:
        return []

    chunk = matches.iloc[0]
    book_id = chunk["book_id"]
    index = int(chunk["chunk_index"])
    start = max(0, index - max(0, before))
    end = index + max(0, after)

    neighbours = rows[
        (rows["book_id"] == book_id)
        & (rows["chunk_index"] >= start)
        & (rows["chunk_index"] <= end)
    ]
    return _normalise_rows(neighbours)


def read_section(chunk_id: str):
    """Read all chunks in the same section as the supplied chunk."""
    table = get_table()
    rows = table.to_pandas()
    if rows.empty:
        return []

    matches = rows[rows["chunk_id"] == chunk_id]
    if matches.empty:
        return []

    chunk = matches.iloc[0]
    book_id = chunk["book_id"]
    section_id = chunk.get("section_id", "")
    if not section_id:
        return read_around(chunk_id, before=0, after=0)

    section_rows = rows[(rows["book_id"] == book_id) & (rows["section_id"] == section_id)]
    return _normalise_rows(section_rows)


def read_chapter(book: str, chapter: str):
    """Read all chunks in a matching chapter for a book id or title."""
    rows = _rows_for_book(book)
    if rows.empty:
        return []

    wanted = chapter.strip()
    wanted_slug = _slugify(wanted)
    lower_wanted = wanted.lower()

    chapter_rows = rows[
        (rows["chapter_id"] == wanted_slug)
        | (rows["chapter_title"].str.lower() == lower_wanted)
        | (rows["chapter_title"].str.lower().str.contains(lower_wanted, na=False, regex=False))
        | (rows["heading_path"].str.lower().str.contains(lower_wanted, na=False, regex=False))
    ]

    return _normalise_rows(chapter_rows)
