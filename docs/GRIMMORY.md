# Grimmory Integration

BookMem can export metadata for Grimmory using sidecar-style JSON files.

BookMem does not write directly into Grimmory's database. The integration is
file-based and designed to work with Grimmory libraries configured to read
sidecar metadata.

Grimmory documentation describes libraries as monitored book folders, with
configurable metadata source behaviour such as embedded-only, sidecar-only,
prefer-sidecar and prefer-embedded. It also documents JSON sidecar metadata
files written alongside book files.

## Commands

Write a sidecar for one BookMem book:

```bash
bookmem grimmory sidecar "data/books/158.../Book.md"
```

Export sidecars for the whole BookMem library:

```bash
bookmem grimmory export data/books --output-dir exports/grimmory
```

Copy BookMem Markdown into the export folder as well:

```bash
bookmem grimmory export data/books --output-dir exports/grimmory --copy-markdown
```

JSON output:

```bash
bookmem grimmory export data/books --output-dir exports/grimmory --json
```

## Output

For each book, BookMem creates a folder and writes:

```text
Book Title - Author/
  Book Title - Author.metadata.json
```

If `--copy-markdown` is used:

```text
Book Title - Author/
  Book Title - Author.md
  Book Title - Author.metadata.json
```

## Metadata fields

Exported sidecars include:

```text
title
subtitle
authors
publisher
publishedDate
description
isbn10
isbn13
language
categories
series
tags
identifiers
BookMem class/topic/routing metadata
```

The file also records:

```json
{
  "generatedBy": "BookMem",
  "source": {
    "provider": "bookmem",
    "sourceBook": "data/books/...",
    "bookId": "..."
  }
}
```

## Recommended Grimmory setup

In Grimmory, configure the relevant library to use or prefer sidecar
metadata, then point the library at the exported folder.

Suggested flow:

```bash
bookmem grimmory export data/books --output-dir /path/to/grimmory/books --copy-markdown
```

Then rescan the Grimmory library.

## Important caveat

Grimmory's exact sidecar schema may evolve. BookMem exports a conservative
JSON structure based on the documented fields and keeps BookMem-specific
fields under a dedicated `bookmem` key.
