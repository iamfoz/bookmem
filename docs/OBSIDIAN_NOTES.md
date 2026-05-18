# Obsidian Notes

BookMem can generate human-facing Markdown notes for Obsidian and similar
personal knowledge systems.

These notes are derived outputs. The canonical book source remains the
cleaned Markdown file in `data/books/`, while summaries, notes, exports and
indexes can be regenerated.

## Output location

Generated notes are written to:

```text
data/notes/
```

Example:

```text
data/notes/
  The 7 Habits of Highly Effective People - Stephen R. Covey - Summary.md
  The 7 Habits of Highly Effective People - Stephen R. Covey - Implementation Notes.md
  The 7 Habits of Highly Effective People - Stephen R. Covey - Book Note.md
```

## Why this exists

BookMem has two audiences:

```text
machines: retrieval, indexing, routing, chunk reading, MCP/API use
humans: review, implementation, reflection, note-making
```

Obsidian notes bridge the two. They let a book move from passive corpus
material into a human knowledge system.

## Commands

List available note templates:

```bash
bookmem notes templates
```

Generate a compact note for one book and preview it:

```bash
bookmem notes generate "data/books/158.../Book.md"
```

Write it to `data/notes/`:

```bash
bookmem notes generate "data/books/158.../Book.md" --write
```

Generate a summary-style note:

```bash
bookmem notes generate "data/books/158.../Book.md" --type summary --write
```

Generate implementation notes:

```bash
bookmem notes generate "data/books/158.../Book.md" --type implementation-notes --write
```

Generate notes for the whole library:

```bash
bookmem notes generate-books data/books --type book-note --write
bookmem notes generate-books data/books --type summary --write
bookmem notes generate-books data/books --type implementation-notes --write
```

Overwrite existing notes:

```bash
bookmem notes generate-books data/books --type summary --write --overwrite
```

## Built-in note types

### `book-note`

Compact book note:

```markdown
---
type: book-note
note_type: book-note
book_id: ...
class: 158
topics:
  - systems
  - personal energy
---

# Book Title

## Core thesis

## Key ideas

## Useful passages

## Related books

## Questions this book can answer
```

### `summary`

Long-form summary report:

```markdown
# Book Title — Summary

## Introduction
## Core Concepts / Ideas
## Interconnections
## Practical Implications
## Integration Table
## Bottom Line / Conclusion
```

This is designed for substantial book summary notes.

### `implementation-notes`

Action-oriented implementation report:

```markdown
# Book Title — Implementation Notes

## 1. Implementation Posture
## 2. Tool-by-tool Setup
## 3. Cadence / Review Rhythm
## 4. Guardrails and Failure Modes
## 5. Metrics and Validation Checks
```

This is designed for books that should change behaviour, systems or
workflows.

## Generated frontmatter

Notes include YAML frontmatter such as:

```yaml
type: book-note
note_type: summary
book_id: stephen_r_covey_the_7_habits_of_highly_effective_people
title: The 7 Habits of Highly Effective People
author: Stephen R. Covey
isbn: "9780795336416"
class: "158"
class_label: Applied psychology and self-improvement
topics:
  - effectiveness
  - habits
  - leadership
routing_aliases:
  - personal_development
  - productivity
source_book: data/books/...
generator: bookmem
generator_version: 0.1.0
review_status: machine_draft
tags:
  - book
  - summary
  - habits
```

## Template configuration

Templates are configured in:

```text
config/note_templates.yaml
config/note_templates.d/
```

Additional templates can be added in `config/note_templates.d/` without
editing the main file.

## Important limitation

The first version is deterministic. It builds useful machine-draft notes
from frontmatter, summaries, topics and indexed passages. It does not
pretend to produce a polished human reading report by itself.

Recommended workflow:

```text
1. Generate deterministic draft note.
2. Review/edit the note in Obsidian.
3. Keep the edited note as a human knowledge artefact.
4. Regenerate only when useful and only with --overwrite when intentional.
```

## Relationship to summaries

`data/summaries/` stores machine-facing summary maps used for retrieval.

`data/notes/` stores human-facing Obsidian notes.

The two are related but intentionally separate.
