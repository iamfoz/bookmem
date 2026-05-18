from __future__ import annotations

from bookmem.frontmatter import find_isbns_in_text, is_valid_isbn10, is_valid_isbn13, normalise_isbn


def test_isbn13_detection_and_normalisation():
    text = "ISBN 978-0-306-40615-7 appears in this book."
    values = find_isbns_in_text(text)
    assert "9780306406157" in values
    assert normalise_isbn("978-0-306-40615-7") == "9780306406157"
    assert is_valid_isbn13("9780306406157")


def test_isbn10_validation():
    assert is_valid_isbn10("0306406152")
    assert normalise_isbn("0-306-40615-2") == "0306406152"


def test_invalid_isbn_is_ignored():
    values = find_isbns_in_text("ISBN 9780306406158")
    assert "9780306406158" not in values
