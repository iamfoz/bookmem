"""Book Markdown file discovery helpers."""

from __future__ import annotations

from pathlib import Path


EXCLUDED_BOOK_FILENAMES = {
    "README.md",
    "README.markdown",
    "CHANGELOG.md",
    "LICENSE.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
}

EXCLUDED_BOOK_DIR_PARTS = {
    ".staging",
    ".git",
    "__pycache__",
    "summaries",
    "notes",
    "manifests",
    "review",
    "graphs",
    "concepts",
    "claims",
    "passages",
    "queries",
    "briefs",
    "reading-lists",
    "restore-points",
    "jobs",
}


def is_book_markdown_file(path: Path) -> bool:
    """Return true when a Markdown file should be treated as a book.

    This deliberately excludes README/support files so sample data directory
    documentation is not prepared, summarised, indexed, cited or exported as
    a book.
    """
    path = Path(path)
    if path.suffix.lower() != ".md":
        return False
    if path.name in EXCLUDED_BOOK_FILENAMES:
        return False
    if path.name.startswith("."):
        return False
    if any(part in EXCLUDED_BOOK_DIR_PARTS or part.startswith(".") for part in path.parts):
        return False
    return True


def discover_book_markdown_files(root: Path | str) -> list[Path]:
    root = Path(root)
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.md") if path.is_file() and is_book_markdown_file(path))
