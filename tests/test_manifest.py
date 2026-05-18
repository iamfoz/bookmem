from __future__ import annotations

from pathlib import Path

from bookmem.manifest import build_prepared_record, load_manifest, manifest_path, markdown_hashes, save_manifest, upsert_book_record


def test_markdown_hashes_include_frontmatter_and_content(fixture_root: Path):
    path = fixture_root / "cleaned" / "Clean Productivity Book - Jane Example - 9780306406157.md"
    hashes = markdown_hashes(path)

    assert hashes["content_hash"]
    assert hashes["frontmatter_hash"]
    assert hashes["full_hash"]


def test_manifest_upsert_round_trip(temp_library: Path):
    path = temp_library / "data" / "books" / "Clean Productivity Book - Jane Example - 9780306406157.md"
    record = build_prepared_record(
        source_path=path,
        canonical_path=path,
        book_id="jane_example_clean_productivity_book",
        classification_source="fixture",
        cleaner_version="test",
    )

    upsert_book_record(record)
    manifest = load_manifest()

    assert manifest["books"]
    assert manifest["books"][0]["book_id"] == "jane_example_clean_productivity_book"
    assert manifest_path().exists()
