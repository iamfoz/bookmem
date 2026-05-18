# Manifest and changed-file detection

BookMem keeps generated operational state in:

```text
data/manifests/books.json
```

The manifest is not the canonical source of book metadata. Canonical metadata lives in the YAML frontmatter at the top of each cleaned Markdown book. The manifest records what BookMem has already prepared and indexed so repeated runs can skip unchanged files.

## Tracked fields

Each book record may contain:

```yaml
book_id: stable id derived from author/title
source_path: original raw Markdown source path
canonical_path: cleaned/indexable Markdown path
content_hash: SHA-256 of the Markdown body, excluding frontmatter
frontmatter_hash: SHA-256 of the YAML frontmatter block
full_hash: SHA-256 of the complete canonical Markdown file
source_content_hash: SHA-256 of the raw source file
last_prepared: when the raw source was last prepared into the canonical library
last_indexed: when the canonical Markdown was last indexed into LanceDB
chunk_count: number of chunks generated at last index time
classification_source: where classification came from, for example folder, filename/content keyword, or Library of Congress
cleaner_version: cleaner version used when preparing the canonical file
```

## Commands

Show current state:

```bash
bookmem status
```

Prepare only raw sources that have changed since their last successful preparation:

```bash
bookmem prepare-books data/raw-books --changed-only
```

Index only new or changed canonical books:

```bash
bookmem ingest --changed-only
```

A full rebuild is still available:

```bash
bookmem ingest --reset
```

## What counts as changed?

For canonical books, BookMem checks both:

```text
content_hash
frontmatter_hash
```

This is deliberate. A body-text change affects retrieval. A frontmatter change affects indexed metadata such as class, aliases, topics and routing.

For raw sources, BookMem checks:

```text
source_content_hash
```

If the raw file has not changed and has already been prepared, `prepare-books --changed-only` skips it.

## Source of truth

The rule remains:

```text
Markdown frontmatter = canonical metadata
Manifest = generated operational state
LanceDB = generated retrieval index
```

You can delete the manifest and rebuild it by preparing/indexing again, but keeping it makes day-to-day runs much faster.


## Summary fields

When book/chapter summaries are generated, the manifest may also track:

```yaml
last_summarised
summary_path
chapter_summary_path
summary_generator_version
chapter_count
```

These fields are generated operational state. They can be rebuilt from the canonical Markdown files under `data/books/`.
