# Book frontmatter

BookMem treats the cleaned Markdown file as the canonical source for indexing. Each indexable book should have YAML frontmatter at the top of the file.

The frontmatter is read as metadata and attached to every indexed chunk. It is not included in the searchable body text.

## Storage model

```text
data/raw-books/
  Original messy exports. Do not edit these.

data/books/
  Cleaned, canonical Markdown books with YAML frontmatter.

data/manifests/
  Generated operational state such as hashes and ingest timestamps.

data/lancedb/
  Generated retrieval index. Can be rebuilt.
```

The rule is:

```text
Markdown frontmatter = canonical metadata
Manifest = generated operational state
LanceDB = generated retrieval index
```

## Example

```yaml
---
bookmem:
  schema_version: 1
  source_type: markdown_book
  source_status: cleaned

title: How to Fail at Almost Everything and Still Win Big
subtitle: Second Edition
author: Scott Adams
isbn:
  ebook: "9798988534969"

classification:
  scheme: BMDC
  primary_class: "158"
  primary_label: Personal improvement and practical psychology
  secondary_classes:
    - "153"
    - "650"
  routing_aliases:
    - personal_development
    - productivity
    - success
    - systems
  topics:
    - systems versus goals
    - personal energy
    - failure
    - talent stacking
    - success
    - habits
    - practical psychology

source:
  original_path: data/raw-books/How to Fail at Almost Everything and Still Win Big, Second Edition - Scott Adams - 9798988534969.md
  cleaned_path: data/books/158-applied-psychology-personal-development/How to Fail at Almost Everything and Still Win Big - Scott Adams.md

ingest:
  include: true
  chunk_profile: standard_nonfiction
  frontmatter_generated_at: "2026-05-18T00:00:00Z"
---

# Preface to the Second Edition
```

## CLI

Show existing frontmatter:

```bash
bookmem frontmatter show "data/books/158-applied-psychology-personal-development/Book.md"
```

Generate suggested frontmatter without writing it:

```bash
bookmem frontmatter generate "data/books/158-applied-psychology-personal-development/Book.md"
```

Write frontmatter to a file that does not already have it:

```bash
bookmem frontmatter generate "data/books/158-applied-psychology-personal-development/Book.md" --write
```

Regenerate and overwrite existing frontmatter:

```bash
bookmem frontmatter generate "data/books/158-applied-psychology-personal-development/Book.md" --write --overwrite
```

Validate frontmatter:

```bash
bookmem frontmatter validate "data/books/158-applied-psychology-personal-development/Book.md"
```

Generate frontmatter for all cleaned books:

```bash
bookmem frontmatter generate-books data/books --write
```

## Classification behaviour

The generator uses this priority order:

1. Existing frontmatter, unless `--overwrite` is supplied.
2. BMDC class inferred from the folder name, for example `158-applied-psychology-personal-development`.
3. Filename-derived title, author and ISBN.
4. Simple topic hints from headings and common terms.
5. `999` unclassified when no class can be inferred.

The generator is intentionally conservative. It creates useful scaffolding, but a human or a stronger model can improve the final metadata later.

## Ingest behaviour

During ingest, BookMem:

1. Reads the YAML frontmatter.
2. Stores metadata such as title, author, BMDC class, aliases and topics.
3. Removes the frontmatter from the body before chunking.
4. Adds the metadata to each LanceDB row.

This prevents metadata clutter from polluting semantic or full-text search.

## Filename-derived metadata

BookMem can infer title, author and ISBN from filenames in this format:

```text
<Title> - <Author> - <ISBN>.md
```

The ISBN segment is optional. This filename metadata is used when generating frontmatter and is recorded under the `metadata` section so the result is auditable:

```yaml
metadata:
  filename_title: How to Fail at Almost Everything and Still Win Big, Second Edition
  filename_author: Scott Adams
  filename_isbn: "9798988534969"
  filename_parse_confidence: high
  classification_source: filename/content keyword
```

The generated title, author and ISBN can then be manually corrected in the YAML frontmatter. Existing frontmatter always wins unless `--overwrite` is used.

See `docs/FILENAME_METADATA.md` for the full convention.

## Poorly named files

If a file does not follow the preferred filename convention, BookMem can still
scan the Markdown body for checksum-validated ISBNs. Those ISBNs can then seed
Library of Congress enrichment.

```bash
bookmem scan-isbns "data/books/unclassified/Book.md"
bookmem frontmatter generate "data/books/unclassified/Book.md" --write
bookmem enrich-loc "data/books/unclassified/Book.md" --write
```
