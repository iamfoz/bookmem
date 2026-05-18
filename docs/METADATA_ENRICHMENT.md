# Metadata Enrichment

BookMem can enrich canonical Markdown frontmatter using optional online
metadata providers.

Provider priority:

```text
1. Library of Congress
2. Open Library
3. Google Books
4. local classifier / existing BookMem inference
```

Open Library's Search API returns work and edition-level data such as title,
authors, first publish year, subjects, publishers, identifiers and edition
keys. Google Books' Volumes API supports book search using the `q` parameter;
ISBN lookups are made with queries such as `isbn:9780306406157`.

## Commands

Enrich from Open Library:

```bash
bookmem enrich-openlibrary "data/books/.../Book.md"
bookmem enrich-openlibrary "data/books/.../Book.md" --write
```

Enrich from Google Books:

```bash
bookmem enrich-google-books "data/books/.../Book.md"
bookmem enrich-google-books "data/books/.../Book.md" --write
```

Run providers in priority order:

```bash
bookmem enrich-metadata "data/books/.../Book.md"
bookmem enrich-metadata "data/books/.../Book.md" --providers loc,openlibrary,google --write
```

JSON output:

```bash
bookmem enrich-metadata "data/books/.../Book.md" --json
```

## Fields

Providers may fill missing fields such as:

```text
title
subtitle
author
ISBN
publisher
published date
language
tags / subjects
description metadata
external identifiers and links
classification, via Library of Congress where available
```

## Source tracking

Every update records provenance in `metadata_sources`:

```yaml
metadata_sources:
  - provider: library_of_congress
    field: classification
    confidence: high
  - provider: open_library
    field: publisher
    confidence: medium
  - provider: google_books
    field: metadata.description
    confidence: high
```

External provider-specific data is stored under:

```yaml
metadata:
  open_library:
    key: /works/...
    edition_key: ...
    source_url: ...
  google_books:
    id: ...
    canonicalVolumeLink: ...
    infoLink: ...
```

## Overwrite behaviour

BookMem does not silently overwrite existing metadata.

Default behaviour:

```text
fill missing fields
merge tags
store alternative external ISBNs under metadata.external_isbns
record metadata sources
preserve existing title/author/publisher/published fields
```

To allow overwriting existing metadata fields:

```bash
bookmem enrich-metadata "Book.md" --write --overwrite
```

To allow Library of Congress classification replacement:

```bash
bookmem enrich-metadata "Book.md" --write --overwrite-classification
```

Use overwrite flags carefully. Human-reviewed frontmatter should normally
remain canonical.

## Google Books API key

Google Books can be called without a key for light use, but you may set:

```env
GOOGLE_BOOKS_API_KEY=...
```

BookMem will include it automatically when present.

## Recommended workflow

```bash
bookmem frontmatter generate "Book.md" --write
bookmem enrich-metadata "Book.md" --providers loc,openlibrary,google --write
bookmem frontmatter validate "Book.md"
bookmem ingest --changed-only
```

## Offline behaviour

Metadata enrichment is optional and online. Normal cleaning, frontmatter,
prepare, indexing and search workflows do not require these providers.
