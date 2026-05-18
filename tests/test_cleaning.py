from __future__ import annotations

from pathlib import Path

from bookmem.clean import clean_markdown_file, clean_markdown_text, load_cleaning_profiles, validate_cleaning_profiles
from bookmem.clean_check import assess_cleanliness


def test_cleaning_profiles_load_and_validate():
    profiles = load_cleaning_profiles()
    assert "epub_pandoc" in profiles
    assert "light_markdown" in profiles
    assert validate_cleaning_profiles() == []


def test_epub_pandoc_cleaner_removes_conversion_noise(tmp_path: Path, fixture_root: Path):
    source = fixture_root / "raw" / "Messy Productivity Book - Jane Example - 9780306406157.md"
    output = tmp_path / "cleaned.md"

    report = clean_markdown_file(source, output_path=output, profile="epub_pandoc")

    cleaned = output.read_text(encoding="utf-8")
    assert report.profile == "epub_pandoc"
    assert report.removed_images >= 1
    assert report.removed_anchors >= 1
    assert report.removed_span_attributes >= 1
    assert "![]" not in cleaned
    assert "<svg>" not in cleaned
    assert "{.CharOverride" not in cleaned
    assert "ISBN 978-0-306-40615-7" not in cleaned
    assert "# Preface" in cleaned or "Preface" in cleaned


def test_light_markdown_profile_preserves_images(fixture_root: Path):
    source = fixture_root / "raw" / "Messy Productivity Book - Jane Example - 9780306406157.md"
    raw = source.read_text(encoding="utf-8")

    cleaned, stats = clean_markdown_text(raw, profile="light_markdown", drop_front_matter=False)

    assert stats["profile"] == "light_markdown"
    assert stats["removed_images"] == 0
    assert "![](cover.jpg)" in cleaned


def test_clean_check_reports_remaining_state(fixture_root: Path):
    source = fixture_root / "cleaned" / "Clean Productivity Book - Jane Example - 9780306406157.md"
    report = assess_cleanliness(source)

    assert report["frontmatter"]["present"] is True
    assert report["isbn"]["count"] >= 1
    assert report["checks"]["images_remaining"] == 0
    assert report["headings"]["heading_count"] >= 2
