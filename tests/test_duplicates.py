from __future__ import annotations

from bookmem.duplicates import find_duplicate_groups, load_book_identities, normalise_title


def test_title_normalisation_moves_leading_the():
    assert normalise_title("The 7 Habits of Highly Effective People") == "7 habits of highly effective people"


def test_duplicate_detection_by_isbn(temp_library):
    identities = load_book_identities(temp_library / "data" / "books", include_raw=False)
    groups = find_duplicate_groups(identities, by="isbn")

    assert any(group.reason == "same ISBN" for group in groups)
    assert any(len(group.books) >= 2 for group in groups)
