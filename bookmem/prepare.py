from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil

from .clean import clean_markdown_file
from .config import get_settings
from .frontmatter import generate_frontmatter, read_markdown_with_frontmatter, write_markdown_with_frontmatter
from .loc import enrich_file_with_loc
from .taxonomy import get_class_label
from .manifest import build_prepared_record, book_identity_from_markdown, source_needs_prepare, upsert_book_record


@dataclass
class PrepareResult:
    source_path: str
    output_path: str
    cleaned: bool
    wrote_file: bool
    moved_file: bool
    title: str
    author: str | None
    isbn: str | None
    primary_class: str
    primary_label: str
    classification_source: str
    skipped: bool = False


INVALID_FILENAME_CHARS_RE = re.compile(r'[\\/:*?"<>|]')
MULTI_SPACE_RE = re.compile(r"\s+")


def class_root_code(class_code: str | None) -> str:
    if not class_code:
        return "999"
    match = re.search(r"\d{3}", str(class_code))
    return match.group(0) if match else "999"


def safe_filename_part(value: str | None, fallback: str = "Unknown") -> str:
    value = (value or fallback).strip()
    value = INVALID_FILENAME_CHARS_RE.sub(" ", value)
    value = value.replace("\n", " ").replace("\r", " ")
    value = MULTI_SPACE_RE.sub(" ", value).strip(" .")
    return value or fallback


def canonical_folder_for_class(class_code: str | None) -> str:
    root = class_root_code(class_code)
    label = get_class_label(root) or "Unclassified"
    label_slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "unclassified"
    return f"{root}-{label_slug}"


def canonical_filename(title: str, author: str | None, isbn: str | None = None) -> str:
    parts = [safe_filename_part(title, "Untitled")]
    if author:
        parts.append(safe_filename_part(author, "Unknown Author"))
    if isbn:
        parts.append(safe_filename_part(isbn, ""))
    return " - ".join(part for part in parts if part) + ".md"


def unique_path(path: Path, overwrite: bool = False) -> Path:
    if overwrite or not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _primary_isbn(frontmatter: dict) -> str | None:
    isbn = frontmatter.get("isbn")
    if isinstance(isbn, dict):
        for key in ("filename", "detected_in_text", "detected_in_text_1", "unknown"):
            if isbn.get(key):
                return str(isbn[key])
        if isbn:
            return str(next(iter(isbn.values())))
    if isinstance(isbn, str) and isbn.strip():
        return isbn.strip()
    return None


def _set_cleaned_path(path: Path) -> None:
    frontmatter, body, had = read_markdown_with_frontmatter(path)
    if not had:
        return
    source = frontmatter.get("source") if isinstance(frontmatter.get("source"), dict) else {}
    source["cleaned_path"] = str(path)
    frontmatter["source"] = source
    write_markdown_with_frontmatter(path, frontmatter, body)


def prepare_book(
    source_path: Path,
    output_root: Path | None = None,
    clean: bool = True,
    enrich_loc: bool = False,
    overwrite_frontmatter: bool = False,
    overwrite_file: bool = False,
    delete_source: bool = False,
    timeout: int = 20,
    changed_only: bool = False,
) -> PrepareResult:
    """Prepare one Markdown book for the canonical BookMem library.

    The function can start from a raw converted Markdown file or a file that is
    already cleaned. It generates frontmatter, optionally enriches by ISBN using
    Library of Congress, computes the final BMDC folder and canonical filename,
    then moves/copies the file into place.
    """
    settings = get_settings()
    output_root = output_root or settings.books_dir
    output_root.mkdir(parents=True, exist_ok=True)

    if changed_only and not source_needs_prepare(source_path):
        return PrepareResult(
            source_path=str(source_path),
            output_path="",
            cleaned=False,
            wrote_file=False,
            moved_file=False,
            title=source_path.stem,
            author=None,
            isbn=None,
            primary_class="",
            primary_label="",
            classification_source="unchanged",
            skipped=True,
        )

    working_path = source_path
    cleaned = False

    if clean:
        # Clean to a temporary staging file first. The final filename depends on
        # frontmatter generated after cleaning.
        staging_dir = output_root / ".staging"
        staging_dir.mkdir(parents=True, exist_ok=True)
        staging_path = unique_path(staging_dir / source_path.name, overwrite=False)
        clean_markdown_file(source_path, output_path=staging_path)
        working_path = staging_path
        cleaned = True
    else:
        if not working_path.exists():
            raise FileNotFoundError(working_path)

    fm_result, frontmatter, _body = generate_frontmatter(
        working_path,
        write=True,
        overwrite=overwrite_frontmatter,
    )

    if enrich_loc:
        enrich_file_with_loc(
            working_path,
            write=True,
            overwrite_classification=overwrite_frontmatter,
            timeout=timeout,
        )
        fm_result, frontmatter, _body = generate_frontmatter(
            working_path,
            write=False,
            overwrite=False,
        )

    classification = frontmatter.get("classification") if isinstance(frontmatter.get("classification"), dict) else {}
    primary_class = str(classification.get("primary_class") or fm_result.primary_class or "999")
    primary_label = str(classification.get("primary_label") or get_class_label(class_root_code(primary_class)) or "Unclassified")
    metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
    classification_source = str(metadata.get("classification_source", fm_result.classification_source))

    title = str(frontmatter.get("title") or fm_result.title or working_path.stem)
    author = str(frontmatter.get("author")) if frontmatter.get("author") else None
    isbn = _primary_isbn(frontmatter)

    folder = output_root / canonical_folder_for_class(primary_class)
    folder.mkdir(parents=True, exist_ok=True)
    final_path = unique_path(folder / canonical_filename(title, author, isbn), overwrite=overwrite_file)

    moved = False
    if working_path.resolve() != final_path.resolve():
        final_path.parent.mkdir(parents=True, exist_ok=True)
        if overwrite_file and final_path.exists():
            final_path.unlink()
        shutil.move(str(working_path), str(final_path))
        moved = True

        # Clean up empty staging dir after move.
        if clean:
            try:
                working_path.parent.rmdir()
            except OSError:
                pass

    _set_cleaned_path(final_path)

    book_id, _author_for_id, _title_for_id = book_identity_from_markdown(final_path)
    upsert_book_record(
        build_prepared_record(
            source_path=source_path,
            canonical_path=final_path,
            book_id=book_id,
            classification_source=classification_source,
            cleaner_version="0.1.0" if cleaned else None,
        )
    )

    if delete_source and clean and source_path.exists():
        source_path.unlink()

    return PrepareResult(
        source_path=str(source_path),
        output_path=str(final_path),
        cleaned=cleaned,
        wrote_file=True,
        moved_file=moved,
        title=title,
        author=author,
        isbn=isbn,
        primary_class=primary_class,
        primary_label=primary_label,
        classification_source=classification_source,
    )
