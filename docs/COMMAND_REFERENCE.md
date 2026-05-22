# Command Reference

This is a practical command index. Use `bookmem <command> --help` for exact options.

## Setup

```bash
bookmem setup presets
bookmem setup run --preset balanced
bookmem setup status
bookmem setup status --include-index
```

## Prepare and ingest

```bash
bookmem clean "Book.md" --profile epub_pandoc
bookmem clean-check "Book.md"
bookmem frontmatter "Book.md" --write
bookmem prepare-books data/raw-books --changed-only
bookmem ingest --changed-only
bookmem ingest --reset
```

## Search and read

```bash
bookmem search "query"
bookmem route "query"
bookmem ask-search "query"
bookmem answer-pack "query" --json
bookmem read-section --chunk-id <chunk_id>
bookmem read-around <chunk_id> --before 2 --after 3
bookmem read-chapter --book <book_id> --chapter "Chapter 6"
```

## Summaries and research layers

```bash
bookmem summarise-books data/books --provider deterministic
bookmem search-summaries "query"
bookmem extract-concepts "Book.md"
bookmem concepts search "concept"
bookmem extract-claims "Book.md"
bookmem claims search "claim"
bookmem claims compare "topic"
bookmem compare-topic "topic"
bookmem passages extract "Book.md"
bookmem passages search "query"
```

## Workspaces and briefs

```bash
bookmem workspace list
bookmem workspace search productivity "query"
bookmem workspace answer-pack finance "query"
bookmem query save "query" --name saved-name
bookmem query run saved-name
bookmem brief generate saved-name
bookmem reading-list --topic "topic"
```

## Imports and enrichment

```bash
bookmem import epub "Book.epub"
bookmem import pdf "Book.pdf"
bookmem import html "Book.html"
bookmem calibre scan "/path/to/Calibre Library"
bookmem enrich-metadata "Book.md" --providers loc,openlibrary,google
```

## Exports

```bash
bookmem export --format jsonl
bookmem export --format llamaindex
bookmem export --format langchain
bookmem graph export --format all
bookmem passages export --format obsidian --output exports/commonplace.md
```

## Services

```bash
bookmem serve
bookmem serve --require-api-key
bookmem serve-mcp
bookmem ui
bookmem tui
```

## Maintenance

```bash
bookmem doctor
bookmem doctor --deep
bookmem jobs list
bookmem audit tail
bookmem backup --output backups/bookmem.tar.gz
bookmem restore backups/bookmem.tar.gz
bookmem migrations status
bookmem migrations apply
```
