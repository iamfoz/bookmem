# Import Adapters

BookMem's canonical source format is cleaned Markdown under `data/books/`.

Import adapters are intentionally a staging layer. They convert source files
into raw Markdown under `data/raw-books/`, then the normal BookMem pipeline
takes over:

```text
import → raw Markdown → clean → frontmatter → classify → prepare → ingest
```

## EPUB

EPUB import is the primary adapter because most ebook exports are EPUB-like
or EPUB-derived.

```bash
bookmem import epub "Book.epub"
```

Custom output directory:

```bash
bookmem import epub "Book.epub" --output-dir data/raw-books
```

JSON output:

```bash
bookmem import epub "Book.epub" --json
```

EPUB import reads the package spine, extracts XHTML/HTML content in reading
order, converts it to simple Markdown-ish text, and writes a raw Markdown
file.

## HTML

```bash
bookmem import html "Book.html"
```

HTML import strips scripts/styles/tags and preserves simple heading and
paragraph structure.

## PDF

```bash
bookmem import pdf "Book.pdf"
```

PDF import uses best-effort text extraction via `pypdf`.

Important caveat:

```text
PDF extraction can be messy, incomplete or badly ordered.
Always review the raw Markdown before preparing/indexing.
```

## Calibre

```bash
bookmem import calibre "/path/to/Calibre Library"
```

Calibre import currently creates metadata stubs from `metadata.db`. It does
not convert the actual ebook files yet.

The stubs are useful for auditing what is in a Calibre library and for later
pairing with EPUB/PDF imports.

## Output

Importers write to:

```text
data/raw-books/
```

Imported files include frontmatter like:

```yaml
---
bookmem_import:
  source_format: epub
  source_path: /path/to/Book.epub
  importer_version: 0.1.0
  status: raw_import
---
```

## Recommended workflow

```bash
bookmem import epub "Book.epub"
bookmem clean-check "data/raw-books/Book.md"
bookmem prepare-books data/raw-books --profile epub_pandoc --changed-only
bookmem ingest --changed-only
```

Or, for a single file:

```bash
bookmem import epub "Book.epub"
bookmem prepare-book "data/raw-books/Book.md" --profile epub_pandoc --enrich-loc
bookmem ingest --changed-only
```

## Why import to raw Markdown first?

This keeps the pipeline inspectable.

Source formats such as EPUB, HTML and PDF are messy in different ways. By
writing raw Markdown first, you can inspect, clean, audit and review before
the book becomes canonical.

## Current limitations

- EPUB conversion uses a stdlib-based HTML-to-Markdown-ish converter. It is
  intentionally conservative, not a full typographic converter.
- PDF import is best-effort and depends on extractable text.
- Calibre import currently creates metadata stubs, not full content imports.
- Importers do not replace cleaning profiles or frontmatter generation.
