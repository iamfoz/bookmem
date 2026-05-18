# Audit Log

BookMem includes a durable JSONL audit log for agent infrastructure.

The audit log is intended to answer:

```text
What changed?
Which command changed it?
Which provider was used?
Was the action successful?
Which files were affected?
```

## Log file

```text
data/audit/bookmem.log.jsonl
```

Each line is one JSON record.

Example:

```json
{
  "timestamp": "2026-05-18T12:00:00+00:00",
  "command": "bookmem enrich-metadata Book.md --write",
  "action": "metadata.enrich_metadata",
  "status": "ok",
  "changed_files": ["data/books/.../Book.md"],
  "provider": "openlibrary,google",
  "target": "data/books/.../Book.md",
  "message": "Ran metadata enrichment provider chain",
  "details": {}
}
```

## Commands

Show recent audit records:

```bash
bookmem audit tail
bookmem audit tail --limit 100
```

JSON output:

```bash
bookmem audit tail --json
```

Search audit records:

```bash
bookmem audit search "enrich"
bookmem audit search "human_review"
bookmem audit search "migrations.apply"
```

Export audit log:

```bash
bookmem audit export --format jsonl
bookmem audit export --format json
```

Export to a file:

```bash
bookmem audit export --format jsonl --output exports/bookmem-audit.jsonl
```

## Automatically audited actions

BookMem now writes audit records for:

```text
migrations.apply
migrations.create
clean_derived
human_review.*
setup.run
metadata.enrich_openlibrary
metadata.enrich_google_books
metadata.enrich_metadata
```

More commands can be instrumented over time.

## Status values

Common status values:

```text
ok
warn
error
rejected
human_reviewed
superseded
```

## Why JSONL?

JSONL is easy to append, stream, grep, parse and import into other tools.

It is also well suited to Sandy/OpenClaw-style agents because each action is
a self-contained event.

## Audit log versus review log

Human review actions still write the specialised review log:

```text
data/review/human_review_log.jsonl
```

They also write to the central audit log:

```text
data/audit/bookmem.log.jsonl
```

The review log is domain-specific. The audit log is system-wide.

## Suggested agent behaviour

Agents should write or inspect audit records when performing significant
actions.

Useful pattern:

```text
1. Run action.
2. Check command status.
3. Inspect latest audit record.
4. Report changed files to the user.
```

## Safety note

The audit log is append-only by convention. BookMem does not currently
prevent manual editing, but tools should avoid modifying old records.


## Restore points and rollback

The audit log is the timeline. Restore points are the recovery mechanism.

Higher-risk write actions can include rollback metadata:

```json
{
  "details": {
    "restore_point_id": "20260518T120000Z-before-change",
    "rollback": {
      "restore_point_id": "20260518T120000Z-before-change"
    }
  }
}
```

Use:

```bash
bookmem restore-points list
bookmem rollback --audit-id "metadata.enrich_metadata"
```

See `docs/RESTORE_POINTS.md`.
