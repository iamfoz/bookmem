from __future__ import annotations

from bookmem.citation_exports import export_references, reference_from_frontmatter, references_from_directory, supported_export_formats, supported_styles


def test_reference_can_be_built_from_frontmatter(fixture_root):
    path = fixture_root / "cleaned" / "Clean Productivity Book - Jane Example - 9780306406157.md"
    reference = reference_from_frontmatter(path)

    assert reference.title == "Clean Productivity Book"
    assert reference.author == "Jane Example"
    assert reference.isbn == "9780306406157"


def test_citation_and_export_formats_are_available():
    assert "apa" in supported_styles()
    assert "bibtex" in supported_export_formats()
    assert "ris" in supported_export_formats()


def test_bibtex_export_contains_book_title(fixture_root):
    references = references_from_directory(fixture_root / "cleaned")
    output = export_references(references, format_name="bibtex")

    assert "@book" in output
    assert "Clean Productivity Book" in output
