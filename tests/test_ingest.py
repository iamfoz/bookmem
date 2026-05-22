from __future__ import annotations

from pathlib import Path

import bookmem.ingest as ingest


def test_ingest_is_idempotent(temp_library: Path, monkeypatch):
    """Re-running a full `ingest` must not accumulate duplicate chunks.

    `embed_texts` and `update_manifest_index_metadata` are stubbed so the test
    needs no embedding model.
    """
    monkeypatch.setattr(
        ingest, "embed_texts", lambda texts: [[0.1, 0.2, 0.3, 0.4] for _ in texts]
    )
    monkeypatch.setattr(ingest, "update_manifest_index_metadata", lambda **kwargs: {})

    from bookmem.search import get_table

    ingest.ingest_books()
    first = get_table().count_rows()

    ingest.ingest_books()
    second = get_table().count_rows()

    assert first > 0, "fixture corpus produced no chunks"
    assert second == first, f"re-ingest duplicated chunks: {first} -> {second}"
