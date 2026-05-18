# Claims

Concepts are reusable models/frameworks.

Claims are assertions.

BookMem can extract, search and compare claims so the corpus becomes more
useful as a research substrate.

## Data file

```text
data/claims/claims.yaml
```

## Claim shape

```yaml
claims:
  - claim_id: ...
    claim: Goals are less useful than systems for long-term success.
    stance: supports
    confidence: medium
    source_chunks:
      - ...
    citation: ...
    tags:
      - goals
      - systems
    review_status: machine_draft
    title: ...
    author: ...
    book_id: ...
    source_path: ...
    heading_path: ...
    evidence: ...
    extracted_at: ...
    extractor: deterministic
```

## Commands

Extract claims from a book:

```bash
bookmem extract-claims "data/books/.../Book.md"
```

Preview without writing:

```bash
bookmem extract-claims "data/books/.../Book.md" --no-write
```

Search claims:

```bash
bookmem claims search "goals"
```

Filter by stance:

```bash
bookmem claims search "goals" --stance supports
bookmem claims search "goals" --stance challenges
bookmem claims search "goals" --stance qualifies
```

Compare claims on a topic:

```bash
bookmem claims compare "compound interest"
```

JSON and Markdown:

```bash
bookmem claims compare "compound interest" --json
bookmem claims compare "goals" --markdown --output exports/goals-claims.md
```

## Stances

```text
supports
challenges
qualifies
neutral
```

## Confidence

```text
low
medium
high
```

The deterministic extractor currently emits mostly `medium` and `low`
confidence. It should be treated as a claim-discovery tool, not final human
scholarship.

## Review status

Extracted claims are marked:

```yaml
review_status: machine_draft
```

## Difference from concepts

A concept might be:

```text
Circle of Influence
```

A claim might be:

```text
People are more effective when they focus on what they can influence.
```

Concepts are reusable names/models. Claims are propositions that can be
supported, challenged, qualified or compared.

## Audit

Claim operations write audit records:

```text
claims.extract
claims.compare
```
