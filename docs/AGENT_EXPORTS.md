# Agent exports

BookMem can export the canonical corpus for other agents and retrieval frameworks.

This is separate from reference-manager exports. Reference-manager exports describe books as academic references. Agent exports describe books and indexed chunks as machine-readable retrieval material.

## Commands

```bash
bookmem export --format jsonl
bookmem export --format llamaindex
bookmem export --format langchain
bookmem export --format markdown-index
bookmem export --format all
```

By default files are written to:

```text
exports/
```

Use another directory with:

```bash
bookmem export --format all --output-dir /tmp/bookmem-agent-export
```

## Common output files

Every export writes:

```text
exports/bookmem_books.json
exports/bookmem_export_manifest.json
```

`bookmem_books.json` contains one record per canonical Markdown book, including title, author, ISBN, BMDC class, routing aliases, topics, summary metadata and chapter summary metadata when available.

`bookmem_export_manifest.json` records when the export was generated, how many books and chunks were exported, and which files were written.

## JSONL chunk export

```bash
bookmem export --format jsonl
```

Writes:

```text
exports/bookmem_chunks.jsonl
```

Each line is one indexed chunk with source metadata, line numbers, heading path and reusable citation text. Embedding vectors are intentionally omitted because they are already stored in LanceDB and are usually not useful in portable exports.

## LlamaIndex export

```bash
bookmem export --format llamaindex
```

Writes:

```text
exports/bookmem_llamaindex_documents.jsonl
```

Each line has the shape:

```json
{
  "id_": "book_id::chunk_000001",
  "text": "chunk text",
  "metadata": {
    "title": "...",
    "author": "...",
    "primary_class": "158",
    "heading_path": "Chapter 6 > Goals Versus Systems",
    "start_line": 1240,
    "end_line": 1288,
    "citation": "..."
  }
}
```

## LangChain export

```bash
bookmem export --format langchain
```

Writes:

```text
exports/bookmem_langchain_documents.jsonl
```

Each line has the shape:

```json
{
  "page_content": "chunk text",
  "metadata": {
    "title": "...",
    "author": "...",
    "primary_class": "158",
    "chunk_id": "..."
  }
}
```

## Markdown agent index

```bash
bookmem export --format markdown-index
```

Writes:

```text
exports/bookmem_agent_tools.md
```

This file is intended for agents and human operators. It describes how to use the BookMem CLI, lists the collection, shows class distribution and includes summary material when available.

## Recommended workflow

Before exporting for other agents, run:

```bash
bookmem prepare-books data/raw-books --changed-only
bookmem summarise-books data/books
bookmem ingest --changed-only
bookmem export --format all
```

If the index has not been built, chunk-based exports will contain zero chunks. `bookmem_books.json` and the Markdown index can still be generated from canonical Markdown frontmatter.
