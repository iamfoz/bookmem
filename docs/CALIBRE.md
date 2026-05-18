# Calibre Integration

BookMem can use a Calibre library as a metadata source.

Calibre does not replace BookMem frontmatter. It is used for enrichment,
audit and import staging.

## Commands

Scan a Calibre library:

```bash
bookmem calibre scan "/path/to/Calibre Library"
```

Search for metadata:

```bash
bookmem calibre metadata "/path/to/Calibre Library" "Book Title"
```

Import Calibre metadata as raw Markdown stubs:

```bash
bookmem calibre import "/path/to/Calibre Library"
```

Enrich a BookMem Markdown file from Calibre:

```bash
bookmem calibre enrich "data/books/158.../Book.md" "/path/to/Calibre Library" --write
```

## Metadata fields

Calibre can provide:

```text
title
author
ISBN
publisher
published date
series
tags
identifiers
formats
Calibre internal ID
Calibre relative path
```

## Design rule

BookMem remains canonical.

```text
Calibre metadata.db = enrichment source
BookMem frontmatter = canonical metadata
LanceDB = generated retrieval index
```

Calibre enrichment stores source metadata under:

```yaml
metadata:
  calibre:
    calibre_id: 123
    path: Author/Title (123)
    formats:
      - EPUB
    identifiers:
      isbn: "978..."
```

## Import stubs

`bookmem calibre import` creates raw Markdown metadata stubs in
`data/raw-books/`. It does not convert ebook content.

Use it for audit, metadata review, or matching with separate EPUB/PDF imports.

## Recommended workflow

```bash
bookmem calibre scan "/path/to/Calibre Library"
bookmem calibre metadata "/path/to/Calibre Library" "The 7 Habits"
bookmem calibre enrich "data/books/.../Book.md" "/path/to/Calibre Library" --write
bookmem frontmatter validate "data/books/.../Book.md"
bookmem ingest --changed-only
```
