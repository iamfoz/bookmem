# Answer Packs

`bookmem answer-pack` builds a structured evidence bundle for answering a
question from the BookMem corpus.

It does not pretend to be the final answer. It collects the material an
agent or human needs in order to answer properly.

## Command

```bash
bookmem answer-pack "What do my books say about systems versus goals?"
```

JSON mode:

```bash
bookmem answer-pack "What do my books say about systems versus goals?" --json
```

Useful options:

```bash
bookmem answer-pack "..." --limit 10
bookmem answer-pack "..." --context 2
bookmem answer-pack "..." --no-summaries
bookmem answer-pack "..." --no-text
bookmem answer-pack "..." --rebuild-graph
```

## Output sections

The pack contains:

```text
Route
Relevant books
Summary matches
Top passages
Read-around context
Related books
Suggested synthesis
Citations
Errors/warnings
```

## JSON shape

```json
{
  "schema_version": 1,
  "answer_pack_version": "0.1.0",
  "query": "What do my books say about systems versus goals?",
  "route": {},
  "relevant_books": [],
  "summary_matches": [],
  "top_passages": [],
  "read_around_context": [],
  "related_books": [],
  "suggested_synthesis": {},
  "citations": [],
  "errors": []
}
```

## Recommended agent workflow

For Sandy or another agent:

```text
1. Call `bookmem answer-pack "<question>" --json`.
2. Inspect route and relevant books.
3. Read top passages and surrounding context.
4. Use citations for every claim.
5. Mention uncertainty if the pack is thin or warnings are present.
```

## Why this is different from `ask-search`

`ask-search` is retrieval-oriented. It finds and displays useful search hits.

`answer-pack` is answer-preparation-oriented. It gathers enough structured
evidence for a downstream agent to produce a grounded answer.

## Citation behaviour

Citations include:

```text
title
author
heading path
line range
chunk id
source path
```

Agents should carry these through into final answers wherever possible.

## Limitations

This command does not locally generate a polished prose answer. That is
deliberate. It prepares evidence; a trusted agent or human can then write the
final synthesis.
