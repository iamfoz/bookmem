# Prompt: Summarise Book

You are generating a BookMem machine-draft summary for a Markdown book.

## Purpose

Produce a retrieval-friendly summary map that helps an agent decide whether
the book is relevant before reading individual chunks.

## Inputs

- Book title
- Author
- BMDC classification
- Existing frontmatter
- Cleaned Markdown book text
- Chapter/section headings where available

## Output format

Return structured JSON only:

```json
{
  "core_thesis": "A concise paragraph stating the book's central argument.",
  "major_ideas": [
    "idea one",
    "idea two"
  ],
  "best_for_questions_about": [
    "topic one",
    "topic two"
  ],
  "keywords": [
    "keyword one",
    "keyword two"
  ],
  "chapters": [
    {
      "title": "Chapter title",
      "summary": "Concise chapter summary.",
      "major_ideas": [
        "chapter idea"
      ],
      "headings": [
        "important heading"
      ],
      "keywords": [
        "chapter keyword"
      ]
    }
  ]
}
```

## Rules

- Do not invent content not supported by the book text.
- Keep summaries useful for search, routing and agent reasoning.
- Prefer precise concepts over vague praise.
- Preserve disagreement, caveats or uncertainty when the text contains them.
- Do not claim the summary is human-reviewed.
- The output will be stored with `review_status: machine_draft`.
