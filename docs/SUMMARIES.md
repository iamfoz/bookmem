# Book and chapter summaries

BookMem stores summaries as **derived files** under `data/summaries/`. They are not the canonical source of truth. The cleaned Markdown book remains canonical; summaries can be deleted and rebuilt at any time.

```text
data/books/
  158-applied-psychology-and-self-improvement/
    How to Fail at Almost Everything and Still Win Big - Scott Adams - 9798988534969.md

data/summaries/
  scott_adams_how_to_fail_at_almost_everything_and_still_win_big_second_edition/
    book.yaml
    chapters.yaml
```

## Why summaries exist

Chunk search is good for finding passages, but books also need a map. The summary layer helps an agent decide which books and chapters are worth reading before it dives into chunk-level retrieval.

A sensible agent retrieval flow is:

```text
1. Search book/chapter summaries.
2. Select likely books and chapters.
3. Search chunks within that narrowed scope.
4. Read neighbouring chunks for context.
5. Answer with citations and book/chapter context.
```

## Commands

Generate summaries for one book:

```bash
bookmem summarise-book "data/books/158-applied-psychology-and-self-improvement/Book.md"
```

Generate summaries for all canonical books:

```bash
bookmem summarise-books data/books
```

Search summaries:

```bash
bookmem search-summaries "systems versus goals"
```

Search only book-level summaries:

```bash
bookmem search-summaries "systems versus goals" --books-only
```

Preview without writing files:

```bash
bookmem summarise-book "data/books/Book.md" --dry-run
```

## Generated files

Each book gets:

```text
data/summaries/<book_id>/book.yaml
data/summaries/<book_id>/chapters.yaml
```

`book.yaml` contains:

```yaml
title: How to Fail at Almost Everything and Still Win Big
author: Scott Adams
core_thesis: >
  Machine-drafted extractive thesis text.
major_ideas:
  - systems versus goals
  - personal energy
  - talent stacking
best_for_questions_about:
  - productivity
  - personal development
  - success
review_status: machine_draft
```

`chapters.yaml` contains a list of chapter summaries with headings, keywords, and source size information.

## Draft quality

The first implementation is deliberately deterministic and offline. It extracts a useful draft map from frontmatter, headings and early chapter text. It does **not** pretend to be a perfect human-quality summary.

All generated summaries include:

```yaml
summary_kind: deterministic_extract
review_status: machine_draft
```

Later versions can add optional LLM-backed summaries while preserving the same output file structure.

## Manifest integration

When summaries are generated, `data/manifests/books.json` is updated with:

```yaml
last_summarised
summary_path
chapter_summary_path
summary_generator_version
chapter_count
```

These fields are operational state. The canonical metadata still lives in the book's YAML frontmatter.
