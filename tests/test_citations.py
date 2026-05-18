from __future__ import annotations

from bookmem.chunking import chunk_markdown_file
from bookmem.search import format_markdown_citation


def test_chunks_include_line_ranges_and_citations(fixture_root):
    path = fixture_root / "cleaned" / "Clean Productivity Book - Jane Example - 9780306406157.md"
    chunks = chunk_markdown_file(path, target_chars=400, overlap_chars=50)

    assert chunks
    first = chunks[0]
    assert first.start_line >= 1
    assert first.end_line >= first.start_line
    assert first.citation
    assert "Clean Productivity Book" in first.citation


def test_markdown_citation_format():
    row = {
        "title": "Clean Productivity Book",
        "author": "Jane Example",
        "heading_path": "Chapter 1 > Systems",
        "start_line": 10,
        "end_line": 20,
        "chunk_id": "example::chunk_000001",
        "source_path": "data/books/example.md",
    }

    citation = format_markdown_citation(row)
    assert "Clean Productivity Book" in citation
    assert "lines 10-20" in citation
    assert "example::chunk_000001" in citation
