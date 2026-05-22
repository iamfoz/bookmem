from __future__ import annotations

from pathlib import Path

from bookmem.frontmatter import infer_class_from_metadata
from bookmem.taxonomy import get_class_label, infer_class_from_path, resolve_alias


def test_productivity_classification_from_metadata():
    primary_class, _label, _source = infer_class_from_metadata(
        title="A Practical Guide to Habits and Productivity",
        author="Jane Example",
        body="systems habits focus personal development self improvement",
        topics=["productivity", "habits", "personal development"],
    )
    assert primary_class in {"158", "650"}


def test_finance_alias_resolves_to_finance_class():
    resolved = resolve_alias("finance")
    classes = set(resolved.get("primary_class", [])) | set(resolved.get("secondary_class", []))
    assert "332" in classes or "330" in classes


def test_class_label_exists_for_common_classes():
    assert get_class_label("158")
    assert get_class_label("332")


def test_class_can_be_inferred_from_path():
    primary_class, _label = infer_class_from_path(
        Path("data/books/158-applied-psychology-and-self-improvement/Book.md"),
        Path("data/books"),
    )
    assert primary_class == "158"
