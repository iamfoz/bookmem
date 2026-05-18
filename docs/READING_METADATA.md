# Reading Metadata

BookMem can infer lightweight reading metadata for canonical Markdown books.

This helps reading-list generation, agent recommendations and collection
statistics.

## Frontmatter shape

```yaml
reading:
  difficulty: beginner
  estimated_pages: 312
  estimated_reading_hours: 8.0
  density: medium
  best_read_as: cover_to_cover
  word_count: 85800
  heading_count: 42
  average_sentence_words: 19.6
  inferred_at: 2026-05-18T12:00:00+00:00
  inference_source: deterministic
  confidence: medium
  review_status: machine_draft
  reading_metadata_version: 0.1.0
```

## Allowed values

Difficulty:

```text
beginner
intermediate
advanced
```

Density:

```text
light
medium
dense
```

Best read as:

```text
cover_to_cover
reference
skim_then_search
```

## Commands

Preview inferred metadata:

```bash
bookmem reading-metadata infer "data/books/.../Book.md"
```

Write to frontmatter:

```bash
bookmem reading-metadata infer "data/books/.../Book.md" --write
```

Overwrite existing non-human-reviewed reading metadata:

```bash
bookmem reading-metadata infer "data/books/.../Book.md" --write --overwrite
```

JSON output:

```bash
bookmem reading-metadata infer "data/books/.../Book.md" --json
```

## Statistics

Show reading difficulty distribution:

```bash
bookmem stats --by-difficulty
```

General stats now include:

```text
books with reading metadata
estimated pages
estimated reading hours
```

## How inference works

The deterministic inference uses simple signals:

```text
word count
estimated pages
estimated reading time
heading count
average sentence length
title/topic hints
density heuristics
reference/manual title hints
```

It is useful, but not a substitute for human judgement.

## Review status

Inferred metadata is marked:

```yaml
review_status: machine_draft
```

If you manually review and correct it, use:

```bash
bookmem review mark-human-reviewed "data/books/.../Book.md"
```

## Reading-list integration

`bookmem reading-list` uses reading metadata when available to improve
suggested reading posture:

```text
Start here
Read early
Then read
Read after the foundations
Use as a reference
Skim, then search
```

## Audit

Writing inferred metadata records:

```text
reading_metadata.infer
```
