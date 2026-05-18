from __future__ import annotations

from pathlib import Path

from bookmem.frontmatter import generate_frontmatter, parse_book_filename, read_markdown_with_frontmatter, validate_frontmatter


def test_filename_metadata_is_parsed():
    parsed = parse_book_filename(Path("Example Book - Jane Example - 9780306406157.md"))
    assert parsed.title == "Example Book"
    assert parsed.author == "Jane Example"
    assert parsed.isbn == "9780306406157"
    assert parsed.confidence == "high"


def test_existing_frontmatter_is_read(fixture_root: Path):
    path = fixture_root / "cleaned" / "Clean Productivity Book - Jane Example - 9780306406157.md"
    frontmatter, body, had_frontmatter = read_markdown_with_frontmatter(path)

    assert had_frontmatter is True
    assert frontmatter["title"] == "Clean Productivity Book"
    assert frontmatter["author"] == "Jane Example"
    assert "Systems beat goals" in body


def test_generate_frontmatter_from_filename_and_body(tmp_path: Path, fixture_root: Path):
    source = fixture_root / "raw" / "Messy Productivity Book - Jane Example - 9780306406157.md"
    path = tmp_path / source.name
    path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    result, frontmatter, body = generate_frontmatter(path, write=False)

    assert result.title == "Messy Productivity Book"
    assert result.author == "Jane Example"
    assert "9780306406157" in str(frontmatter.get("isbn"))
    assert frontmatter["classification"]["primary_class"] in {"158", "650", "999"}


def test_validate_frontmatter_accepts_fixture(fixture_root: Path):
    path = fixture_root / "cleaned" / "Clean Productivity Book - Jane Example - 9780306406157.md"
    issues = validate_frontmatter(path)
    assert issues == []
