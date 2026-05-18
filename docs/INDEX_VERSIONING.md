# Index Versioning

BookMem tracks the versions and settings that produced the current retrieval
index.

This prevents subtle bugs where the LanceDB index still exists, but was
generated using older chunking, embeddings, cleaning or taxonomy settings.

## Manifest metadata

The manifest can now store:

```yaml
index_metadata:
  index_schema_version: 3
  chunker_version: 0.4.0
  embedding_provider: sentence_transformers
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  embedding_dimension: 384
  cleaner_version: 0.2.0
  cleaning_profile: epub_pandoc
  taxonomy_version: sha256:...
  bookmem_version: 0.37.0
  chunk_count: 18420
  book_count: 214
```

Individual book records also receive the current index fingerprint when they
are indexed.

## Command

```bash
bookmem index-status
```

JSON output:

```bash
bookmem index-status --json
```

Record the current fingerprint without reindexing:

```bash
bookmem index-status --update-manifest
```

Use `--update-manifest` carefully. It is mainly useful when you know the
index is correct but the manifest predates index metadata.

## Example output

```text
Index stale: yes

Reason:
- chunker version changed: stored='0.3.0', current='0.4.0'
- cleaner version changed: stored='0.1.0', current='0.2.0'
- embedding model changed: stored='old-model', current='sentence-transformers/all-MiniLM-L6-v2'
```

## What is checked

```text
index_schema_version
chunker_version
embedding_provider
embedding_model
embedding_dimension
cleaner_version
cleaning_profile
taxonomy_version
LanceDB readability
LanceDB table existence
row count
```

## When to reindex

Reindex when `bookmem index-status` reports stale reasons.

Full rebuild:

```bash
bookmem ingest --reset
```

Changed-only rebuild:

```bash
bookmem ingest --changed-only
```

If chunking, embeddings, schema or taxonomy changed, prefer:

```bash
bookmem ingest --reset
```

## Why taxonomy hash?

Taxonomy labels, aliases and classes influence routing and indexed metadata.
BookMem therefore stores a short SHA-256 fingerprint of the taxonomy file.

## Why embedding dimension?

A LanceDB vector table created with one embedding dimension may not be valid
for a different embedding model. Tracking dimension makes that failure
obvious before search quality silently degrades.
