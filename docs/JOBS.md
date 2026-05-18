# Jobs and Observability

BookMem includes a lightweight jobs ledger for long-running workflows.

This gives CLI/TUI/API layers a consistent place to read operational status.

## Files

```text
data/jobs/
  <job_id>.json
  <job_id>.log
```

## Status JSON

Each job JSON file tracks:

```yaml
job_id: ...
started_at: ...
finished_at: ...
status: active|ok|warn|error|cancelled
command: ...
progress: 0.0
current_file: ...
files_processed: 0
errors: []
warnings: []
message: ...
jobs_version: 0.1.0
```

## Commands

List jobs:

```bash
bookmem jobs list
```

Filter by status:

```bash
bookmem jobs list --status active
bookmem jobs list --status error
```

Show job status:

```bash
bookmem jobs status <job_id>
```

JSON:

```bash
bookmem jobs status <job_id> --json
```

Tail job log:

```bash
bookmem jobs tail <job_id>
bookmem jobs tail <job_id> --lines 200
```

## Status values

```text
active
ok
warn
error
cancelled
```

## Developer helpers

Future long-running commands can use:

```python
from bookmem.jobs import JobTracker

with JobTracker("ingest changed books") as job:
    job.update(progress=0.25, current_file="Book.md", files_processed=10)
    job.log("Processed Book.md")
```

Or lower-level helpers:

```python
from bookmem.jobs import start_job, update_job, finish_job

job = start_job("prepare books")
update_job(job.job_id, progress=0.5, current_file="Book.md")
finish_job(job.job_id, status="ok")
```

## Why this matters

Long-running processes need more than a spinner. A job record lets another
process inspect what is happening:

```text
TUI progress panels
API status endpoints
future background workers
container logs
agent status reports
troubleshooting after failure
```

## Relationship to audit

Jobs answer:

```text
What is running, how far through is it, and what happened while it ran?
```

Audit answers:

```text
What changed and when?
```

Both are useful. They should not replace each other.

## Future instrumentation targets

Good candidates for job tracking:

```text
prepare-books
ingest
summarise-books
extract-concepts
extract-claims
passages extract
import calibre
backup/restore
setup run
eval retrieval
graph build/export
```
