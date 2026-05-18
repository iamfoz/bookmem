from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
import difflib
import re
from typing import Any, Iterable

import yaml

from .config import get_settings
from .frontmatter import (
    find_isbns_in_text,
    parse_book_filename,
    read_markdown_with_frontmatter,
)
from .chunking import FRONTMATTER_RE

DUPLICATE_DETECTOR_VERSION = "0.1.0"


@dataclass
class BookIdentity:
    path: Path
    collection: str
    title: str | None = None
    author: str | None = None
    book_id: str | None = None
    isbns: list[str] = field(default_factory=list)
    content_hash: str | None = None
    content_fingerprint: str | None = None
    has_frontmatter: bool = False

    @property
    def path_text(self) -> str:
        return str(self.path)


@dataclass
class DuplicateGroup:
    reason: str
    score: float
    key: str
    books: list[BookIdentity]
    details: list[str] = field(default_factory=list)


def normalise_text(value: str | None) -> str:
    if not value:
        return ""
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalise_title(value: str | None) -> str:
    text = normalise_text(value)
    text = re.sub(r"\b(the|a|an)\b", " ", text)
    text = re.sub(r"\b(second|third|fourth|fifth|revised|updated|edition|ed)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalise_author(value: str | None) -> str:
    text = normalise_text(value)
    # Handle simple catalogue-style names: "Surname, Forename".
    if value and "," in value:
        parts = [normalise_text(part) for part in value.split(",")]
        if len(parts) >= 2:
            text = f"{parts[1]} {parts[0]}".strip()
    return text


def title_author_key(title: str | None, author: str | None) -> str:
    return f"{normalise_title(title)}|{normalise_author(author)}"


def content_hash_for_body(body: str) -> str:
    normalised = body.replace("\r\n", "\n").replace("\r", "\n")
    normalised = re.sub(r"[ \t]+", " ", normalised)
    normalised = re.sub(r"\n{3,}", "\n\n", normalised).strip()
    return sha256(normalised.encode("utf-8")).hexdigest()


def fingerprint_body(body: str, max_chars: int = 12000) -> str:
    text = re.sub(r"\W+", " ", body.lower())
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    third = max_chars // 3
    return " ".join([text[:third], text[len(text) // 2: len(text) // 2 + third], text[-third:]])


def _metadata_from_frontmatter(path: Path, frontmatter: dict[str, Any], body: str, had_frontmatter: bool, collection: str) -> BookIdentity:
    title = frontmatter.get("title") if isinstance(frontmatter, dict) else None
    author = frontmatter.get("author") if isinstance(frontmatter, dict) else None
    bookmem_meta = frontmatter.get("bookmem") if isinstance(frontmatter.get("bookmem"), dict) else {}
    book_id = bookmem_meta.get("book_id") or frontmatter.get("book_id")

    isbns: list[str] = []
    isbn_data = frontmatter.get("isbn") if isinstance(frontmatter, dict) else None
    if isinstance(isbn_data, dict):
        for value in isbn_data.values():
            if value:
                isbns.append(str(value))
    elif isinstance(isbn_data, str):
        isbns.append(isbn_data)

    for isbn in find_isbns_in_text(body):
        if isbn not in isbns:
            isbns.append(isbn)

    parsed = parse_book_filename(path)
    if not title:
        title = parsed.title
    if not author:
        author = parsed.author
    if parsed.isbn and parsed.isbn not in isbns:
        isbns.append(parsed.isbn)

    return BookIdentity(
        path=path,
        collection=collection,
        title=str(title).strip() if title else None,
        author=str(author).strip() if author else None,
        book_id=str(book_id).strip() if book_id else None,
        isbns=sorted(set(isbns)),
        content_hash=content_hash_for_body(body),
        content_fingerprint=fingerprint_body(body),
        has_frontmatter=had_frontmatter,
    )


def load_book_identity(path: Path, collection: str) -> BookIdentity:
    try:
        frontmatter, body, had_frontmatter = read_markdown_with_frontmatter(path)
    except Exception:
        text = path.read_text(encoding="utf-8", errors="replace")
        match = FRONTMATTER_RE.match(text)
        body = text[match.end():] if match else text
        frontmatter = {}
        had_frontmatter = bool(match)
    return _metadata_from_frontmatter(path, frontmatter, body, had_frontmatter, collection)


def discover_markdown_files(books_dir: Path | None = None, raw_dir: Path | None = None, include_raw: bool = True) -> list[tuple[Path, str]]:
    settings = get_settings()
    roots: list[tuple[Path, str]] = [(books_dir or settings.books_dir, "canonical")]
    candidate_raw = raw_dir or Path("data/raw-books")
    if include_raw and candidate_raw.exists():
        roots.append((candidate_raw, "raw"))

    files: list[tuple[Path, str]] = []
    seen: set[Path] = set()
    for root, collection in roots:
        if not root.exists():
            continue
        for path in sorted(root.glob("**/*.md")):
            if ".staging" in path.parts:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append((path, collection))
    return files


def load_book_identities(books_dir: Path | None = None, raw_dir: Path | None = None, include_raw: bool = True) -> list[BookIdentity]:
    return [load_book_identity(path, collection) for path, collection in discover_markdown_files(books_dir, raw_dir, include_raw)]


def _groups_from_mapping(reason: str, mapping: dict[str, list[BookIdentity]], score: float = 1.0) -> list[DuplicateGroup]:
    groups: list[DuplicateGroup] = []
    for key, books in sorted(mapping.items()):
        unique = []
        seen: set[Path] = set()
        for book in books:
            resolved = book.path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                unique.append(book)
        if len(unique) > 1:
            groups.append(DuplicateGroup(reason=reason, score=score, key=key, books=unique))
    return groups


def find_duplicate_groups(
    books: Iterable[BookIdentity],
    by: str = "all",
    similarity_threshold: float = 0.88,
) -> list[DuplicateGroup]:
    books_list = list(books)
    groups: list[DuplicateGroup] = []

    if by in {"all", "isbn"}:
        by_isbn: dict[str, list[BookIdentity]] = {}
        for book in books_list:
            for isbn in book.isbns:
                by_isbn.setdefault(isbn, []).append(book)
        groups.extend(_groups_from_mapping("same ISBN", by_isbn, score=1.0))

    if by in {"all", "title-author"}:
        by_title_author: dict[str, list[BookIdentity]] = {}
        for book in books_list:
            key = title_author_key(book.title, book.author)
            if key != "|" and len(key) > 3:
                by_title_author.setdefault(key, []).append(book)
        groups.extend(_groups_from_mapping("same normalised title and author", by_title_author, score=1.0))

    if by in {"all", "content"}:
        by_content: dict[str, list[BookIdentity]] = {}
        for book in books_list:
            if book.content_hash:
                by_content.setdefault(book.content_hash, []).append(book)
        groups.extend(_groups_from_mapping("same content hash", by_content, score=1.0))

    if by in {"all", "near"}:
        # Near-duplicate pass. This is intentionally O(n^2), because personal book
        # libraries are usually hundreds or low thousands of files, not millions.
        for idx, left in enumerate(books_list):
            for right in books_list[idx + 1:]:
                if left.path.resolve() == right.path.resolve():
                    continue
                title_score = difflib.SequenceMatcher(
                    None,
                    normalise_title(left.title),
                    normalise_title(right.title),
                ).ratio()
                author_score = difflib.SequenceMatcher(
                    None,
                    normalise_author(left.author),
                    normalise_author(right.author),
                ).ratio() if left.author and right.author else 0.0
                content_score = difflib.SequenceMatcher(
                    None,
                    left.content_fingerprint or "",
                    right.content_fingerprint or "",
                ).ratio()

                # Weighted so a near-identical title and author can flag different
                # editions, while genuinely similar content can catch ugly re-exports.
                combined = max(
                    (title_score * 0.75) + (author_score * 0.25),
                    content_score,
                )
                if combined >= similarity_threshold:
                    details = [
                        f"title similarity: {title_score:.0%}",
                        f"author similarity: {author_score:.0%}",
                        f"content similarity: {content_score:.0%}",
                    ]
                    groups.append(DuplicateGroup(
                        reason="near-duplicate similarity",
                        score=combined,
                        key=f"{left.path.name} <> {right.path.name}",
                        books=[left, right],
                        details=details,
                    ))

    return deduplicate_groups(groups)


def deduplicate_groups(groups: list[DuplicateGroup]) -> list[DuplicateGroup]:
    seen: set[tuple[str, tuple[str, ...]]] = set()
    results: list[DuplicateGroup] = []
    reason_priority = {
        "same ISBN": 0,
        "same content hash": 1,
        "same normalised title and author": 2,
        "near-duplicate similarity": 3,
    }
    for group in sorted(groups, key=lambda g: (reason_priority.get(g.reason, 99), -g.score, g.key)):
        paths = tuple(sorted(str(book.path.resolve()) for book in group.books))
        key = (group.reason, paths)
        if key in seen:
            continue
        seen.add(key)
        results.append(group)
    return results


def duplicate_groups_to_yaml(groups: list[DuplicateGroup]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "detector_version": DUPLICATE_DETECTOR_VERSION,
        "generated_by": "bookmem duplicates",
        "groups": [
            {
                "reason": group.reason,
                "score": round(group.score, 4),
                "key": group.key,
                "details": group.details,
                "review": {"status": "pending", "action": None, "notes": None},
                "books": [
                    {
                        "path": book.path_text,
                        "collection": book.collection,
                        "title": book.title,
                        "author": book.author,
                        "book_id": book.book_id,
                        "isbns": book.isbns,
                        "content_hash": book.content_hash,
                        "has_frontmatter": book.has_frontmatter,
                    }
                    for book in group.books
                ],
            }
            for group in groups
        ],
    }


def write_duplicate_review(groups: list[DuplicateGroup], output: Path | None = None) -> Path:
    output_path = output or Path("data/review/possible_duplicates.yaml")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(duplicate_groups_to_yaml(groups), sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )
    return output_path
