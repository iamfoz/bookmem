# Passages and Commonplace Book

BookMem includes a curated quote/passages layer.

This bridges machine retrieval and a human commonplace-book workflow.

## Data files

```text
data/passages/
  extracted.yaml
  favourites.yaml
```

## Passage shape

```yaml
quote: ...
summary: ...
why_it_matters: ...
source_chunk: ...
citation: ...
tags:
  - energy management
review_status: machine_draft
```

BookMem also stores helpful metadata:

```yaml
passage_id: ...
title: ...
author: ...
book_id: ...
source_path: ...
heading_path: ...
created_at: ...
favourite: false
```

## Commands

Extract passages from a book:

```bash
bookmem passages extract "data/books/.../Book.md"
```

Preview extraction without writing:

```bash
bookmem passages extract "data/books/.../Book.md" --no-write
```

Add tags:

```bash
bookmem passages extract "data/books/.../Book.md" --tag productivity --tag systems
```

Search passages:

```bash
bookmem passages search "energy management"
```

Favourite a passage or chunk:

```bash
bookmem passages favourite <chunk_id>
bookmem passages favourite <chunk_id> --tag energy --note "Useful for planning decisions"
```

Export as an Obsidian commonplace book:

```bash
bookmem passages export --format obsidian --output exports/commonplace.md
```

Other export formats:

```bash
bookmem passages export --format jsonl --output exports/passages.jsonl
bookmem passages export --format yaml --output exports/passages.yaml
```

Export favourites only:

```bash
bookmem passages export --format obsidian --favourites-only --output exports/favourites.md
```

## Review status

Extracted passages are machine drafts:

```yaml
review_status: machine_draft
```

This means they are useful leads, not human-curated quotes.

You can later mark the YAML file as human-reviewed:

```bash
bookmem review mark-human-reviewed data/passages/extracted.yaml
bookmem review mark-human-reviewed data/passages/favourites.yaml
```

## How extraction works

The initial extractor is deterministic and conservative:

```text
paragraph-based
avoids very short fragments
avoids very long passages
favours paragraphs containing explanatory/strategic terms
records provenance
marks results as machine_draft
```

It is not intended to replace deliberate human selection. It is designed to
provide a good first pass for later review.

## Obsidian export

Obsidian export produces:

```markdown
# Commonplace Book

## Book Title

> Quote text...

**Summary:** ...
**Why it matters:** ...
**Tags:** #systems #energy-management
```

## Audit

Passage operations write audit records:

```text
passages.extract
passages.favourite
passages.export
```
