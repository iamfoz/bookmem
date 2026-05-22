from __future__ import annotations

import pytest

import bookmem.search as search


@pytest.fixture
def tiny_table(monkeypatch, tmp_path):
    """A minimal LanceDB table that mirrors BookMem's ingest output.

    `embed_texts` is stubbed so the test needs no embedding model.
    """
    import lancedb
    import pandas as pd

    rows = [
        {
            "vector": [0.10, 0.20, 0.30, 0.40],
            "text": "systems beat goals over the long run",
            "chunk_id": "habits::chunk_000001",
            "title": "Atomic Habits",
            "book_id": "habits",
            "primary_class": "158",
            "secondary_class_text": "",
        },
        {
            "vector": [0.40, 0.30, 0.20, 0.10],
            "text": "compound interest rewards patient saving",
            "chunk_id": "money::chunk_000001",
            "title": "The Psychology of Money",
            "book_id": "money",
            "primary_class": "332",
            "secondary_class_text": "",
        },
    ]
    db = lancedb.connect(str(tmp_path / "lancedb"))
    table = db.create_table("book_chunks_test", data=pd.DataFrame(rows))
    table.create_fts_index("text", replace=True)

    monkeypatch.setattr(search, "get_table", lambda: table)
    monkeypatch.setattr(
        search, "embed_texts", lambda texts: [[0.12, 0.22, 0.32, 0.42] for _ in texts]
    )
    return table


def test_hybrid_search_supplies_query_vector(tiny_table):
    # Regression: hybrid search (the default mode) must not ask LanceDB to
    # embed the query string — BookMem registers no embedding function on the
    # table, so doing so raises "No embedding function for vector".
    results = search.search_books("systems versus goals", limit=5, mode="hybrid")
    assert isinstance(results, list)
    assert results


def test_vector_search_works(tiny_table):
    results = search.search_books("systems", limit=5, mode="vector")
    assert isinstance(results, list)
    assert results


def test_fts_search_works(tiny_table):
    results = search.search_books("compound", limit=5, mode="fts")
    assert isinstance(results, list)
    assert any("compound" in (row.get("text") or "") for row in results)


def test_hybrid_search_with_class_filter(tiny_table):
    results = search.search_books(
        "saving and interest", limit=5, class_code=["332"], mode="hybrid"
    )
    assert isinstance(results, list)
    assert all(str(row.get("primary_class")) == "332" for row in results)
