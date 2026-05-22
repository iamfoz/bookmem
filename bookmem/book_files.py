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

    `path` is interpreted as a corpus-relative path: only its in-corpus
    components are examined (see `discover_book_markdown_files`). This
    deliberately excludes README/support files and BookMem's own data
    subdirectories so documentation and derived state are not prepared,
    summarised, indexed, cited or exported as books.
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
    """Return book Markdown files found anywhere under `root`.

    Exclusion rules are evaluated against each file's path *relative to* `root`,
    so a corpus stored under a hidden directory — such as the Hermes runtime
    home at ~/.hermes/bookmem — is not wrongly skipped because of the leading
    dot-directory in its absolute path.
    """
    root = Path(root)
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*.md")
        if path.is_file() and is_book_markdown_file(path.relative_to(root))
    )
