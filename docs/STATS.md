# Collection Statistics

BookMem can report collection-level statistics for the canonical Markdown library.

This is useful for spotting whether the corpus is balanced, whether particular classes dominate the library, whether books are missing author/topic metadata, and whether the index is up to date.

## Commands

```bash
bookmem stats
bookmem stats --by-class
bookmem stats --by-author
bookmem stats --by-topic
bookmem stats --json
```

By default, `bookmem stats` shows overall totals plus the top class, author and topic breakdowns.

Use `--limit` to control the number of rows shown:

```bash
bookmem stats --by-class --limit 50
```

Use `--books-dir` to inspect a non-default canonical library:

```bash
bookmem stats --books-dir /path/to/books
```

## Reported totals

The summary panel includes:

- total books
- indexed books
- indexed chunks
- books needing indexing
- unclassified books
- books without author metadata
- books without topic metadata
- books with ISBN metadata

## Breakdown reports

### By class

```bash
bookmem stats --by-class
```

Shows BMDC class distribution, including book count, chunk count and author count per class.

### By author

```bash
bookmem stats --by-author
```

Shows which authors have the most books in the corpus and which BMDC classes they appear in.

### By topic

```bash
bookmem stats --by-topic
```

Shows topic distribution based on canonical frontmatter.

This report is only as good as the `classification.topics` metadata in each cleaned Markdown file.

## JSON output

```bash
bookmem stats --json
```

This emits machine-readable JSON for dashboards, scheduled reports or agent workflows.

## Data sources

Statistics are calculated from:

1. canonical Markdown files under `data/books/`
2. YAML frontmatter in those files
3. the manifest at `data/manifests/books.json`, when present

The manifest is used for indexed chunk counts and changed-file status. If a book has not yet been indexed, its chunk count will be shown as zero until `bookmem ingest` has run.
