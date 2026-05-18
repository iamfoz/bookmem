# Concept Extraction

BookMem can extract reusable concepts, models, frameworks and methods from
books into a derived concept layer.

This is more useful for agent reasoning than ordinary passage search alone.
It lets an assistant agent ask questions such as:

```text
Which books contain reusable models I can apply to planning?
Which books discuss a decision framework like Circle of Influence?
What concepts appear in class 158 books?
```

## Derived files

Per-book concept files:

```text
data/concepts/<book_id>/concepts.yaml
```

Search index:

```text
data/concepts/concepts.json
```

These are derived artefacts. They can be deleted and rebuilt from the
canonical Markdown library.

## Commands

Extract concepts from one book:

```bash
bookmem extract-concepts "data/books/.../Book.md"
```

Preview only:

```bash
bookmem extract-concepts "data/books/.../Book.md" --dry-run
```

Extract concepts for all books:

```bash
bookmem concepts extract-books data/books
```

Rebuild the concept index:

```bash
bookmem concepts rebuild-index
```

Search concepts:

```bash
bookmem concepts search "circle of influence"
```

List concepts:

```bash
bookmem concepts list
bookmem concepts list --class 158
bookmem concepts list --type model
```

JSON output:

```bash
bookmem concepts search "systems thinking" --json
bookmem concepts list --class 158 --json
```

## Concept record shape

```yaml
concepts:
  - concept_id: covey_7_habits_circle_of_influence
    name: Circle of Influence
    type: model
    aliases:
      - influence circle
    description: Short faithful description.
    useful_for:
      - planning
      - decision-making
    limitations: []
    book_id: covey_7_habits
    title: The 7 Habits of Highly Effective People
    author: Stephen R. Covey
    primary_class: "158"
    topics:
      - habits
      - effectiveness
    source_chunks:
      - chunk_id: ...
        citation: ...
        source_path: ...
        heading_path: ...
        start_line: 124
        end_line: 170
    confidence: 0.7
    extractor: deterministic
    review_status: machine_draft
```

## Extractor behaviour

The first extractor is deterministic. It looks for candidate named models,
frameworks, principles, methods and warning concepts in chunk text.

It is deliberately conservative enough to be useful, but not perfect. All
output is marked:

```yaml
review_status: machine_draft
```

## Concept types

Common types include:

```text
model
framework
principle
method
warning
concept
```

## Recommended workflow

```bash
bookmem ingest --changed-only
bookmem concepts extract-books data/books
bookmem concepts search "planning"
bookmem concepts list --class 158
```

For agent use:

```text
1. Search concepts first.
2. Use source_chunks to read the supporting passages.
3. Cite the source chunks when making claims.
4. Treat machine-draft concepts as useful leads, not final truth.
```
