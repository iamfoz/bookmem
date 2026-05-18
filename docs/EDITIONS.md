# Edition Handling

BookMem distinguishes between duplicate books and legitimate multiple
editions of the same underlying work.

Duplicate detection is useful, but it should not treat every title/author
match as a mistake. A library may legitimately contain a first edition,
revised edition, anniversary edition or updated edition.

## Frontmatter fields

BookMem uses two related frontmatter blocks.

### `work`

The work identifies the underlying intellectual work.

```yaml
work:
  work_id: covey_7_habits
  canonical_title: The 7 Habits of Highly Effective People
```

### `edition`

The edition identifies the specific version of that work.

```yaml
edition:
  label: Second Edition
  number: 2
  year: 2024
  is_revised: true
```

## Commands

List all editions:

```bash
bookmem editions
```

Filter by title, author, ISBN or work ID:

```bash
bookmem editions "The 7 Habits of Highly Effective People"
```

Infer missing work/edition fields during listing:

```bash
bookmem editions --ensure
```

Write inferred fields to frontmatter:

```bash
bookmem editions --write
```

Overwrite existing work/edition fields:

```bash
bookmem editions --write --overwrite
```

JSON output:

```bash
bookmem editions --json
```

## Relationship to duplicates

Edition handling lets BookMem distinguish:

```text
same ISBN, duplicate
same work, different edition
same work, possible duplicate
same title/author, maybe duplicate
same content hash, definite duplicate
```

## Inference

BookMem can infer simple edition data from titles such as:

```text
Second Edition
Third Edition
Revised Edition
Updated Edition
25th Anniversary Edition
```

It can also infer a year from the `published` frontmatter field when
available.

## Human review remains important

Work and edition inference is helpful, but not perfect. If a book has a
known edition history, edit the frontmatter manually.

Example:

```yaml
work:
  work_id: covey_7_habits
  canonical_title: The 7 Habits of Highly Effective People

edition:
  label: 30th Anniversary Edition
  number:
  year: 2020
  is_revised: true
```

## Recommended workflow

```bash
bookmem prepare-books data/raw-books --changed-only
bookmem editions --ensure
bookmem editions --write
bookmem duplicates --write-review
bookmem review duplicates
```
