# Topic Comparison / Disagreement Mapping

BookMem can compare how books treat a topic.

This helps agents avoid bland consensus summaries by identifying supportive,
critical and mixed/context-dependent stances.

## Command

```bash
bookmem compare-topic "goals"
```

JSON:

```bash
bookmem compare-topic "goals" --json
```

Markdown:

```bash
bookmem compare-topic "goals" --markdown
```

Save output:

```bash
bookmem compare-topic "goals" --markdown --output exports/goals-comparison.md
bookmem compare-topic "risk" --json --output exports/risk-comparison.json
```

## Output

Example shape:

```text
Books favouring goals:
- Book A

Books criticising goals:
- Book B

Mixed / context-dependent:
- Book C

Tensions:
- Goals can direct attention, but systems drive repeatable behaviour.
```

## Data sources

The deterministic comparison engine uses:

```text
curated passages
book summaries
chunk search
citations
heading paths
```

## Stance groups

```text
favouring
criticising
mixed
neutral
```

## Review status

Topic comparisons are marked:

```yaml
review_status: machine_draft
```

The result is a useful research map, not a final scholarly judgement.

## Why this matters

A normal answer might say:

```text
Books say goals are useful.
```

A better answer says:

```text
Some books treat goals as useful for direction, while others argue systems,
habits or feedback loops matter more for actual progress.
```

That is the difference between retrieval and synthesis.

## Method

The first implementation uses deterministic stance heuristics. It looks for
supportive and critical language around the topic and then groups evidence by
book.

This can later be upgraded with optional LLM-assisted stance extraction.
