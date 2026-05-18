from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import hashlib
import json
from typing import Any

from .chunking import FRONTMATTER_RE, parse_frontmatter, slugify
from .config import get_settings

MANIFEST_VERSION = 1
DEFAULT_MANIFEST_PATH = Path("data/manifests/books.json")


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def split_frontmatter_text(text: str) -> tuple[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return "", text
    return match.group(1), text[match.end():]


def markdown_hashes(path: Path) -> tuple[str, str, str]:
    """Return (content_hash, frontmatter_hash, full_hash).

    content_hash is body-only so indexing can ignore pure metadata changes when
    wanted. frontmatter_hash tracks routing/classification changes, which do
    affect indexed metadata and should normally trigger re-indexing.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    fm_text, body = split_frontmatter_text(text)
    return sha256_text(body), sha256_text(fm_text), sha256_text(text)


def manifest_path(path: Path | None = None) -> Path:
    if path:
        return path
    settings = get_settings()
    if getattr(settings, "manifest_path", None):
        return settings.manifest_path
    # Keep the manifest beside the configured books dir by default when using a
    # non-standard project layout.
    candidate = settings.books_dir.parent / "manifests" / "books.json"
    return candidate


def relative_or_absolute(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except Exception:
        return str(path)


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    mpath = manifest_path(path)
    if not mpath.exists():
        return {"version": MANIFEST_VERSION, "books": []}
    data = json.loads(mpath.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", MANIFEST_VERSION)
    data.setdefault("books", [])
    return data


def save_manifest(data: dict[str, Any], path: Path | None = None) -> None:
    mpath = manifest_path(path)
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")


def _record_matches(record: dict[str, Any], *, book_id: str | None = None, canonical_path: str | None = None, source_path: str | None = None) -> bool:
    if book_id and record.get("book_id") == book_id:
        return True
    if canonical_path and record.get("canonical_path") == canonical_path:
        return True
    if source_path and record.get("source_path") == source_path:
        return True
    return False


def upsert_book_record(record: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    data = load_manifest(path)
    books = data.setdefault("books", [])
    book_id = record.get("book_id")
    canonical_path = record.get("canonical_path")
    source_path = record.get("source_path")

    for idx, existing in enumerate(books):
        if _record_matches(existing, book_id=book_id, canonical_path=canonical_path, source_path=source_path):
            merged = {**existing, **{k: v for k, v in record.items() if v is not None}}
            books[idx] = merged
            save_manifest(data, path)
            return merged

    books.append(record)
    save_manifest(data, path)
    return record


def get_record_for_path(book_path: Path, path: Path | None = None) -> dict[str, Any] | None:
    target = relative_or_absolute(book_path)
    target_resolved = str(book_path.resolve())
    for record in load_manifest(path).get("books", []):
        for key in ("canonical_path", "source_path"):
            value = record.get(key)
            if value == target or value == target_resolved:
                return record
            if value:
                try:
                    if Path(value).resolve() == book_path.resolve():
                        return record
                except Exception:
                    pass
    return None


def book_identity_from_markdown(path: Path, books_dir: Path | None = None) -> tuple[str, str | None, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    frontmatter, _body = parse_frontmatter(text)
    title = str(frontmatter.get("title") or path.stem).strip()
    author_value = frontmatter.get("author")
    author = str(author_value).strip() if author_value else None
    book_id = slugify(f"{author or ''}_{title}")
    return book_id, author, title


def classification_source_from_frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    frontmatter, _body = parse_frontmatter(text)
    metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
    return str(metadata.get("classification_source") or "")


def build_prepared_record(
    *,
    source_path: Path,
    canonical_path: Path,
    book_id: str,
    chunk_count: int | None = None,
    classification_source: str | None = None,
    cleaner_version: str | None = None,
) -> dict[str, Any]:
    content_hash, frontmatter_hash, full_hash = markdown_hashes(canonical_path)
    return {
        "book_id": book_id,
        "source_path": relative_or_absolute(source_path),
        "canonical_path": relative_or_absolute(canonical_path),
        "content_hash": content_hash,
        "frontmatter_hash": frontmatter_hash,
        "full_hash": full_hash,
        "last_prepared": utc_now_iso(),
        "last_indexed": None,
        "chunk_count": chunk_count,
        "classification_source": classification_source,
        "cleaner_version": cleaner_version,
        "source_content_hash": sha256_file(source_path) if source_path.exists() else None,
    }


def mark_indexed(
    *,
    canonical_path: Path,
    book_id: str,
    chunk_count: int,
    classification_source: str | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    content_hash, frontmatter_hash, full_hash = markdown_hashes(canonical_path)
    existing = get_record_for_path(canonical_path, path) or {}
    record = {
        **existing,
        "book_id": book_id,
        "canonical_path": relative_or_absolute(canonical_path),
        "content_hash": content_hash,
        "frontmatter_hash": frontmatter_hash,
        "full_hash": full_hash,
        "last_indexed": utc_now_iso(),
        "chunk_count": chunk_count,
        "classification_source": classification_source or existing.get("classification_source"),
    }
    return upsert_book_record(record, path)


@dataclass
class BookStatus:
    path: Path
    book_id: str
    title: str
    content_changed: bool
    frontmatter_changed: bool
    indexed: bool
    chunk_count: int | None
    classification_source: str

    @property
    def needs_index(self) -> bool:
        return (not self.indexed) or self.content_changed or self.frontmatter_changed


def status_for_book(path: Path, manifest_file: Path | None = None) -> BookStatus:
    content_hash, frontmatter_hash, _full_hash = markdown_hashes(path)
    book_id, _author, title = book_identity_from_markdown(path)
    record = get_record_for_path(path, manifest_file)
    indexed = bool(record and record.get("last_indexed"))
    return BookStatus(
        path=path,
        book_id=book_id,
        title=title,
        content_changed=not record or record.get("content_hash") != content_hash,
        frontmatter_changed=not record or record.get("frontmatter_hash") != frontmatter_hash,
        indexed=indexed,
        chunk_count=record.get("chunk_count") if record else None,
        classification_source=classification_source_from_frontmatter(path),
    )


def source_needs_prepare(source_path: Path, manifest_file: Path | None = None) -> bool:
    source_hash = sha256_file(source_path)
    source_str = relative_or_absolute(source_path)
    for record in load_manifest(manifest_file).get("books", []):
        if record.get("source_path") == source_str and record.get("source_content_hash") == source_hash and record.get("last_prepared"):
            return False
        try:
            if record.get("source_path") and Path(record["source_path"]).resolve() == source_path.resolve() and record.get("source_content_hash") == source_hash and record.get("last_prepared"):
                return False
        except Exception:
            pass
    return True
