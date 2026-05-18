"""Optional metadata enrichment providers for BookMem.

Provider priority:

1. Library of Congress
2. Open Library
3. Google Books
4. local classifier / existing BookMem inference

This module never overwrites reviewed metadata unless explicitly instructed.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import os
import re
from typing import Any
from urllib.parse import urlencode

import requests

from .frontmatter import read_markdown_with_frontmatter, write_markdown_with_frontmatter
from .loc import lookup_loc_by_isbn, enrich_file_with_loc


ENRICHMENT_VERSION = "0.1.0"


@dataclass
class ProviderResult:
    provider: str
    matched: bool
    confidence: str
    fields: dict[str, Any]
    raw: dict[str, Any]
    reason: str | None = None


def _normalise_isbn(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        for candidate in value.values():
            found = _normalise_isbn(candidate)
            if found:
                return found
        return None
    text = re.sub(r"[^0-9Xx]", "", str(value))
    if len(text) in (10, 13):
        return text
    return None


def _isbn_from_frontmatter(frontmatter: dict[str, Any]) -> str | None:
    return _normalise_isbn(frontmatter.get("isbn"))


def _query_from_frontmatter(frontmatter: dict[str, Any], path: Path) -> str:
    isbn = _isbn_from_frontmatter(frontmatter)
    if isbn:
        return f"isbn:{isbn}"
    title = frontmatter.get("title") or path.stem
    author = frontmatter.get("author")
    if author:
        return f"{title} {author}"
    return str(title)


def _field_source(provider: str, field: str, confidence: str, source: str | None = None) -> dict[str, Any]:
    item = {
        "provider": provider,
        "field": field,
        "confidence": confidence,
        "enrichment_version": ENRICHMENT_VERSION,
    }
    if source:
        item["source"] = source
    return item


def _append_metadata_source(frontmatter: dict[str, Any], provider: str, field: str, confidence: str, source: str | None = None) -> None:
    sources = frontmatter.get("metadata_sources")
    if not isinstance(sources, list):
        sources = []
    sources.append(_field_source(provider, field, confidence, source))
    frontmatter["metadata_sources"] = sources


def _set_if_allowed(
    frontmatter: dict[str, Any],
    key: str,
    value: Any,
    provider: str,
    confidence: str,
    overwrite: bool,
    source: str | None = None,
) -> bool:
    if value in (None, "", [], {}):
        return False
    if frontmatter.get(key) and not overwrite:
        return False
    frontmatter[key] = value
    _append_metadata_source(frontmatter, provider, key, confidence, source)
    return True


def _merge_tags(existing: Any, new_values: list[str]) -> list[str]:
    values = []
    if isinstance(existing, list):
        values.extend(str(v) for v in existing if str(v).strip())
    elif existing:
        values.append(str(existing))
    values.extend(str(v) for v in new_values if str(v).strip())
    seen = set()
    out = []
    for value in values:
        key = value.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(value.strip())
    return out


def lookup_openlibrary(isbn: str | None = None, query: str | None = None, timeout: int = 20) -> ProviderResult:
    if isbn:
        params = {"isbn": isbn, "limit": "1"}
    elif query:
        params = {"q": query, "limit": "1"}
    else:
        return ProviderResult("open_library", False, "none", {}, {}, "No ISBN or query supplied.")

    url = "https://openlibrary.org/search.json?" + urlencode(params)
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "BookMem metadata enrichment"})
    response.raise_for_status()
    data = response.json()

    docs = data.get("docs") or []
    if not docs:
        return ProviderResult("open_library", False, "none", {}, data, "No results.")

    doc = docs[0]
    fields: dict[str, Any] = {}

    if doc.get("title"):
        fields["title"] = doc.get("title")
    authors = doc.get("author_name") or []
    if authors:
        fields["author"] = ", ".join(authors)
    if doc.get("publisher"):
        fields["publisher"] = doc["publisher"][0]
    if doc.get("first_publish_year"):
        fields["published"] = str(doc.get("first_publish_year"))
    if doc.get("isbn"):
        fields["isbn"] = {"open_library": doc["isbn"][0]}
    if doc.get("subject"):
        fields["tags"] = [str(item) for item in doc["subject"][:12]]
    if doc.get("language"):
        fields["language"] = doc["language"][0]
    if doc.get("key"):
        fields.setdefault("metadata", {})["open_library"] = {
            "key": doc.get("key"),
            "edition_key": (doc.get("edition_key") or [None])[0],
            "cover_i": doc.get("cover_i"),
            "source_url": f"https://openlibrary.org{doc.get('key')}",
        }

    confidence = "high" if isbn else "medium"
    return ProviderResult("open_library", True, confidence, fields, doc)


def lookup_google_books(isbn: str | None = None, query: str | None = None, timeout: int = 20) -> ProviderResult:
    if isbn:
        q = f"isbn:{isbn}"
    elif query:
        q = query
    else:
        return ProviderResult("google_books", False, "none", {}, {}, "No ISBN or query supplied.")

    params = {"q": q, "maxResults": "1"}
    api_key = os.getenv("GOOGLE_BOOKS_API_KEY")
    if api_key:
        params["key"] = api_key

    url = "https://www.googleapis.com/books/v1/volumes?" + urlencode(params)
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "BookMem metadata enrichment"})
    response.raise_for_status()
    data = response.json()

    items = data.get("items") or []
    if not items:
        return ProviderResult("google_books", False, "none", {}, data, "No results.")

    item = items[0]
    info = item.get("volumeInfo") or {}
    fields: dict[str, Any] = {}

    if info.get("title"):
        fields["title"] = info.get("title")
    if info.get("subtitle"):
        fields["subtitle"] = info.get("subtitle")
    authors = info.get("authors") or []
    if authors:
        fields["author"] = ", ".join(authors)
    if info.get("publisher"):
        fields["publisher"] = info.get("publisher")
    if info.get("publishedDate"):
        fields["published"] = info.get("publishedDate")
    if info.get("description"):
        fields.setdefault("metadata", {})["description"] = info.get("description")
    if info.get("categories"):
        fields["tags"] = [str(item) for item in info.get("categories", [])]
    if info.get("language"):
        fields["language"] = info.get("language")

    identifiers = info.get("industryIdentifiers") or []
    isbn_values = {}
    for ident in identifiers:
        ident_type = ident.get("type")
        ident_value = ident.get("identifier")
        if ident_type and ident_value:
            isbn_values[str(ident_type).lower()] = ident_value
    if isbn_values:
        fields["isbn"] = {"google_books": next(iter(isbn_values.values()))}
        fields.setdefault("metadata", {})["google_books_identifiers"] = isbn_values

    fields.setdefault("metadata", {})["google_books"] = {
        "id": item.get("id"),
        "canonicalVolumeLink": info.get("canonicalVolumeLink"),
        "infoLink": info.get("infoLink"),
        "previewLink": info.get("previewLink"),
    }

    confidence = "high" if isbn else "medium"
    return ProviderResult("google_books", True, confidence, fields, item)


def _merge_metadata(frontmatter: dict[str, Any], value: dict[str, Any], provider: str, confidence: str, overwrite: bool) -> bool:
    if not value:
        return False
    existing = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
    changed = False
    for key, nested in value.items():
        if key in existing and not overwrite:
            continue
        existing[key] = nested
        changed = True
        _append_metadata_source(frontmatter, provider, f"metadata.{key}", confidence)
    if changed:
        frontmatter["metadata"] = existing
    return changed


def apply_provider_result(
    frontmatter: dict[str, Any],
    result: ProviderResult,
    overwrite: bool = False,
) -> list[str]:
    if not result.matched:
        return []

    changed: list[str] = []
    for key, value in result.fields.items():
        if key == "metadata" and isinstance(value, dict):
            if _merge_metadata(frontmatter, value, result.provider, result.confidence, overwrite):
                changed.append("metadata")
            continue

        if key == "tags":
            merged = _merge_tags(frontmatter.get("tags"), value if isinstance(value, list) else [str(value)])
            if merged != frontmatter.get("tags"):
                frontmatter["tags"] = merged
                _append_metadata_source(frontmatter, result.provider, "tags", result.confidence)
                changed.append("tags")
            continue

        if key == "isbn":
            if frontmatter.get("isbn") and not overwrite:
                # Preserve canonical/user ISBN but still record external identifiers.
                existing_meta = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
                existing_meta.setdefault("external_isbns", {})
                existing_meta["external_isbns"][result.provider] = value
                frontmatter["metadata"] = existing_meta
                _append_metadata_source(frontmatter, result.provider, "metadata.external_isbns", result.confidence)
                changed.append("metadata.external_isbns")
                continue

        if _set_if_allowed(frontmatter, key, value, result.provider, result.confidence, overwrite):
            changed.append(key)

    return changed


def enrich_with_openlibrary(book_path: Path, write: bool = False, overwrite: bool = False, timeout: int = 20) -> dict[str, Any]:
    frontmatter, body, _had = read_markdown_with_frontmatter(book_path)
    isbn = _isbn_from_frontmatter(frontmatter)
    query = _query_from_frontmatter(frontmatter, book_path)
    result = lookup_openlibrary(isbn=isbn, query=None if isbn else query, timeout=timeout)
    changed = apply_provider_result(frontmatter, result, overwrite=overwrite)
    if write and changed:
        write_markdown_with_frontmatter(book_path, frontmatter, body)
    return {"provider": "open_library", "matched": result.matched, "changed": changed, "result": asdict(result)}


def enrich_with_google_books(book_path: Path, write: bool = False, overwrite: bool = False, timeout: int = 20) -> dict[str, Any]:
    frontmatter, body, _had = read_markdown_with_frontmatter(book_path)
    isbn = _isbn_from_frontmatter(frontmatter)
    query = _query_from_frontmatter(frontmatter, book_path)
    result = lookup_google_books(isbn=isbn, query=None if isbn else query, timeout=timeout)
    changed = apply_provider_result(frontmatter, result, overwrite=overwrite)
    if write and changed:
        write_markdown_with_frontmatter(book_path, frontmatter, body)
    return {"provider": "google_books", "matched": result.matched, "changed": changed, "result": asdict(result)}


def enrich_metadata(
    book_path: Path,
    providers: list[str] | None = None,
    write: bool = False,
    overwrite: bool = False,
    overwrite_classification: bool = False,
    timeout: int = 20,
) -> dict[str, Any]:
    providers = providers or ["loc", "openlibrary", "google"]
    results: list[dict[str, Any]] = []

    for provider in providers:
        key = provider.strip().lower()
        if key in {"loc", "library_of_congress", "library-of-congress"}:
            # Use existing LoC enrichment implementation for classification.
            try:
                result = enrich_file_with_loc(
                    book_path,
                    write=write,
                    overwrite_classification=overwrite_classification,
                    timeout=timeout,
                )
                results.append({"provider": "library_of_congress", "result": result})
            except Exception as exc:
                results.append({"provider": "library_of_congress", "error": str(exc)})
        elif key in {"openlibrary", "open_library", "open-library"}:
            try:
                results.append(enrich_with_openlibrary(book_path, write=write, overwrite=overwrite, timeout=timeout))
            except Exception as exc:
                results.append({"provider": "open_library", "error": str(exc)})
        elif key in {"google", "google_books", "google-books"}:
            try:
                results.append(enrich_with_google_books(book_path, write=write, overwrite=overwrite, timeout=timeout))
            except Exception as exc:
                results.append({"provider": "google_books", "error": str(exc)})
        else:
            results.append({"provider": provider, "error": "Unknown provider."})

    return {
        "book": str(book_path),
        "providers": providers,
        "write": write,
        "overwrite": overwrite,
        "overwrite_classification": overwrite_classification,
        "results": results,
    }
