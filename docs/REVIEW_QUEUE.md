# Review Queue

BookMem deliberately treats automatic metadata extraction and classification as useful drafts rather than unquestionable truth.

The review queue is a generated operational layer. It helps you find books that need human judgement before the library becomes a trusted agent retrieval source.

## Files

Review files are written under:

```text
data/review/
  needs_metadata.yaml
  needs_classification.yaml
  low_confidence_matches.yaml
```

These files are generated from the canonical Markdown files in `data/books/`. They are safe to delete and regenerate.

## Commands

Generate or refresh all review queues:

```bash
bookmem review
```

Show classification issues:

```bash
bookmem review classifications
```

Show metadata issues:

```bash
bookmem review metadata
```

Show ISBN conflicts, duplicate ISBNs and catalogue/class conflicts:

```bash
bookmem review isbn-conflicts
```

Show lower-confidence classification matches:

```bash
bookmem review low-confidence
```

Apply approved edits:

```bash
bookmem review apply
```

## What gets flagged

BookMem currently flags:

- Missing author
- Missing title
- Multiple checksum-valid ISBNs found in one book
- Possible duplicate ISBNs across files
- Possible duplicate title/author pairs across files
- External catalogue class conflicts with the current BookMem class
- Unclassified books
- Classification confidence below the review threshold
- Books whose frontmatter explicitly sets `classification_review_required: true`

## Applying reviews

The review files are YAML. To approve a classification fix, edit an issue like this:

```yaml
review:
  status: approved
  approved_primary_class: '158'
  approved_primary_label: Applied psychology and self-improvement
  approved_secondary_classes:
    - '153'
  approved_routing_aliases:
    - personal_development
    - productivity
  approved_topics:
    - systems
    - habits
    - personal energy
```

Then run:

```bash
bookmem review apply
```

BookMem updates the Markdown frontmatter and marks the classification as manually reviewed:

```yaml
metadata:
  classification_source: manual_review
  classification_reviewed: true
  classification_confidence: 1.0
```

## Metadata fixes

For metadata issues, approve fields such as:

```yaml
review:
  status: approved
  suggested_author: Scott Adams
```

or:

```yaml
review:
  status: approved
  canonical_isbn: '9798988534969'
```

## Important behaviour

`bookmem review apply` only updates frontmatter. It does not delete duplicates, move files, or rename books automatically.

After applying reviews, run:

```bash
bookmem status
bookmem ingest --changed-only
```

If you want a reviewed book to be renamed or moved into the folder that matches its new classification, run the prepare workflow explicitly, for example:

```bash
bookmem prepare-book "data/books/999-unclassified/Book.md" --no-clean --overwrite-frontmatter
```
