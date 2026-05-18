# Retrieval Evaluation

BookMem includes a simple retrieval benchmark/evaluation set so search
quality can be measured rather than guessed.

## Query set

Default query file:

```text
eval/queries.yaml
```

Example:

```yaml
queries:
  - id: systems_vs_goals
    query: systems versus goals
    expected_books:
      - How to Fail at Almost Everything and Still Win Big
    expected_topics:
      - systems
      - goals
```

Expected books are matched against result titles. Expected topics are
matched against retrieved result metadata and text.

## Commands

List evaluation queries:

```bash
bookmem eval queries
```

Run retrieval evaluation:

```bash
bookmem eval retrieval
```

JSON output:

```bash
bookmem eval retrieval --json
```

Custom query file:

```bash
bookmem eval retrieval --query-file eval/my_queries.yaml
```

Change Recall@K:

```bash
bookmem eval retrieval --k 10
```

Disable routing:

```bash
bookmem eval retrieval --no-route
```

## Metrics

### Recall@K

Recall@K is `1` for a query if at least one expected book/topic appears in
the top K results, otherwise `0`.

Overall Recall@K is the average across queries.

### MRR

Mean Reciprocal Rank rewards expected matches that appear higher in the
result list.

```text
match at rank 1 = 1.0
match at rank 2 = 0.5
match at rank 5 = 0.2
no match = 0.0
```

## Example output

```text
Retrieval evaluation

Queries: 5
Recall@5: 0.86
MRR: 0.72
Failed queries: 1

Failed queries:
- risk_and_return: risk and return
```

## Recommended workflow

Run evaluation before and after changing:

```text
chunking
embedding model
routing aliases
taxonomy
cleaning profiles
summary generation
graph/concept extraction
```

Example:

```bash
bookmem eval retrieval --json > eval/before.json
bookmem embeddings reindex --model bge-m3
bookmem eval retrieval --json > eval/after.json
```

## Important limitation

This is not a full academic IR benchmark. It is a practical regression
harness for your corpus. Improve it by adding queries that reflect the kinds
of questions Sandy should answer.
