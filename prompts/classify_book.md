# Prompt: Classify Book

You are classifying a book for BookMem.

## Purpose

Choose the best BMDC class and routing aliases for a book so agents can
search only the relevant part of the corpus.

## Inputs

- Title
- Author
- ISBN/catlogue metadata, if available
- Frontmatter
- Table of contents/headings
- Representative book text

## Output format

Return structured JSON only:

```json
{
  "primary_class": "158",
  "primary_label": "Applied psychology and self-improvement",
  "secondary_classes": ["650"],
  "routing_aliases": ["productivity", "personal_development"],
  "topics": ["habits", "systems", "personal effectiveness"],
  "confidence": 0.86,
  "reason": "Why this classification is appropriate.",
  "review_required": false
}
```

## Rules

- Prefer the most specific useful BMDC class.
- Use secondary classes when a book genuinely spans fields.
- Do not overfit classification based only on title marketing language.
- Flag `review_required: true` when confidence is low.
- Do not overwrite human-reviewed classification without explicit permission.
