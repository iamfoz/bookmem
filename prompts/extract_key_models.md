# Prompt: Extract Key Models

You are extracting reusable models, frameworks and concepts from a BookMem
book.

## Purpose

Build a concept layer that helps agents answer questions such as:

- Which books contain practical decision models?
- Which frameworks apply to this situation?
- Where have similar ideas appeared elsewhere?

## Inputs

- Book summary
- Chapter summaries
- Relevant passages and citations
- Existing topic/class metadata

## Output format

Return structured JSON only:

```json
{
  "concepts": [
    {
      "name": "Concept or model name",
      "type": "model|framework|principle|method|metaphor|warning",
      "aliases": ["alternate name"],
      "description": "Short faithful description.",
      "useful_for": ["use case"],
      "limitations": ["caveat"],
      "source_citations": ["citation id or line range"]
    }
  ]
}
```

## Rules

- Extract concepts that are reusable, not every minor point.
- Prefer named models and clearly described methods.
- Include limitations or context where relevant.
- Do not invent names for concepts unless clearly marked as descriptive.
- Keep citations attached to extracted concepts.
