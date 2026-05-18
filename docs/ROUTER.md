# Query Router

BookMem includes a deterministic query router so agents can ask the corpus where to search before retrieving chunks.

The router is deliberately simple in this version. It does not call an LLM. It scores a query against:

- BMDC routing aliases
- BMDC class labels and aliases
- BookMem domain hint phrases
- Common topic words such as investing, habits, systems, leadership, sleep, AI and writing

The output is a small JSON object that can be consumed by an agent.

## Route a query

```bash
bookmem route "What do my books say about compound interest?"
```

Example output:

```json
{
  "query": "What do my books say about compound interest?",
  "aliases": ["finance", "investing"],
  "class_codes": ["332", "330"],
  "confidence": 0.92,
  "reason": "The query concerns money, investing, financial markets or personal finance.",
  "matched_terms": ["compound interest"],
  "router_version": "0.1.0"
}
```

## Search using the router

```bash
bookmem ask-search "What do my books say about compound interest?"
```

`ask-search` performs:

```text
route query -> search selected BMDC classes -> read surrounding context
```

If no routed results are found, it can fall back to a broad search unless disabled:

```bash
bookmem ask-search "risk" --no-fallback
```

## Search summaries first

The router can also be used with summaries:

```bash
bookmem ask-search "systems versus goals" --summaries-first
```

This helps an agent identify likely books or chapters before reading chunk-level passages.

## Deterministic first, LLM later

The router is intentionally deterministic for now. That makes it fast, testable and safe to run offline.

A future LLM router can be added as a separate optional mode, but it should not replace deterministic routing as the default behaviour.
