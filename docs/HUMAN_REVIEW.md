# Human Review Workflow

BookMem marks many generated artefacts as machine drafts:

```yaml
review_status: machine_draft
```

This is good. A machine draft can be useful, but it is not trusted library
knowledge until a human reviews it.

The human review workflow lets you promote, reject or mark generated outputs
without pretending they were manually checked.

## Review statuses

```text
machine_draft
needs_human_review
human_reviewed
rejected
superseded
```

## Commands

List machine drafts:

```bash
bookmem review machine-drafts
bookmem review machine-drafts --json
```

Approve a summary:

```bash
bookmem review approve-summary <book_id>
```

Approve all concepts for a book:

```bash
bookmem review approve-concepts <book_id>
```

Reject one concept:

```bash
bookmem review reject-concept <concept_id>
bookmem review reject-concept <concept_id> --reason "Too vague / false positive"
```

Mark any YAML or Markdown artefact as human-reviewed:

```bash
bookmem review mark-human-reviewed data/summaries/<book_id>/book.yaml
bookmem review mark-human-reviewed data/books/.../Book.md
```

Set status explicitly:

```bash
bookmem review set-summary-status <book_id> needs_human_review
bookmem review set-concepts-status <book_id> superseded
```

Optional reviewer metadata:

```bash
bookmem review approve-summary <book_id> --reviewer "Martyn"
bookmem review reject-concept <concept_id> --reviewer "Martyn" --reason "Not a reusable model"
```

## Summary approval

`approve-summary` updates:

```text
data/summaries/<book_id>/book.yaml
data/summaries/<book_id>/chapters.yaml
```

It sets:

```yaml
review_status: human_reviewed
reviewed_at: ...
reviewed_by: ...
```

## Concept approval

`approve-concepts` updates every concept in:

```text
data/concepts/<book_id>/concepts.yaml
```

It also syncs:

```text
data/concepts/concepts.json
```

## Concept rejection

`reject-concept` does not delete the concept. It marks it:

```yaml
review_status: rejected
rejected_at: ...
rejection_reason: ...
```

Keeping rejected concepts visible is useful because it prevents the same
false positive being silently re-trusted later.

## Review log

Review actions are recorded in:

```text
data/review/human_review_log.jsonl
```

Example:

```json
{
  "timestamp": "2026-05-18T12:00:00+00:00",
  "action": "reject_concept",
  "target": "covey_7_habits_circle_of_influence",
  "status": "rejected",
  "detail": {
    "reason": "duplicate concept"
  }
}
```

## Recommended workflow

```bash
bookmem review machine-drafts
bookmem review approve-summary <book_id>
bookmem review approve-concepts <book_id>
bookmem review reject-concept <concept_id> --reason "false positive"
bookmem concepts rebuild-index
```

## Why this matters

Agents can use machine drafts as leads, but should treat
`human_reviewed` artefacts as more trusted.

A useful distinction:

```text
machine_draft     good lead
needs_human_review agent should be cautious
human_reviewed    trusted library knowledge
rejected          do not use as a trusted concept/summary
superseded        replaced by newer output
```
