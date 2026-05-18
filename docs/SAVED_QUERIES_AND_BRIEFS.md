# Saved Queries and Research Briefs

Saved queries turn recurring research questions into reusable BookMem assets.
Research briefs turn those queries into generated evidence reports.

## Files

Saved queries live in:

```text
data/queries/
  systems-thinking.yaml
  personal-finance.yaml
```

Generated briefs live in:

```text
data/briefs/<query-name>/
  <timestamp>.json
  <timestamp>.md
```

## Save a query

```bash
bookmem query save "systems versus goals" --name systems-goals
```

With a workspace:

```bash
bookmem query save "risk and return" --name risk-return --workspace finance
```

With tags:

```bash
bookmem query save "habit design" --name habit-design --workspace productivity --tag habits --tag productivity
```

## List queries

```bash
bookmem query list
bookmem query list --json
```

## Run a saved query

```bash
bookmem query run systems-goals
```

JSON:

```bash
bookmem query run systems-goals --json
```

Update `last_run_at` when running:

```bash
bookmem query run systems-goals --update-last-run
```

## Generate a brief

```bash
bookmem brief generate systems-goals
```

JSON output:

```bash
bookmem brief generate systems-goals --json
```

Do not update `last_run_at`:

```bash
bookmem brief generate systems-goals --no-update-last-run
```

Generate only JSON, not Markdown:

```bash
bookmem brief generate systems-goals --no-markdown
```

## Saved query shape

```yaml
schema_version: 1
name: systems-goals
query: systems versus goals
workspace: productivity
description: Systems versus goals recurring research query.
tags:
  - systems
  - productivity
limit: 8
context: 1
include_concepts: true
include_topic_map: true
include_changed_since_last_run: true
created_at: 2026-05-18T12:00:00+00:00
last_run_at:
```

## Brief contents

A generated brief includes:

```text
best books
top passages
related concepts
topic map
newly added/changed books since last run
changed summaries since last run
suggested synthesis
citations
full answer pack
```

## Why this matters

Saved queries make BookMem proactive rather than merely searchable.

Instead of asking the same question from scratch, an agent can run:

```bash
bookmem brief generate systems-goals
```

and get a current evidence bundle showing what is relevant and what has
changed since the previous run.

## Recommended workflow

```bash
bookmem query save "systems versus goals" --name systems-goals --workspace productivity
bookmem brief generate systems-goals
bookmem audit tail
```

Later:

```bash
bookmem brief generate systems-goals
```

The brief will include changes since the previous run if manifest timestamps
are available.

## Audit

Saving queries and generating briefs write audit records:

```text
query.save
brief.generate
```
