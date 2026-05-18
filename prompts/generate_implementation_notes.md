# Prompt: Generate Implementation Notes

You are generating BookMem implementation notes for a book.

## Purpose

Convert a book's useful ideas into practical implementation guidance for a
human knowledge and task system.

## Inputs

- Book summary
- Chapter summaries
- Useful passages and citations
- Existing topics/classes
- User's preferred implementation style, if provided

## Output structure

```markdown
# {Book Title} — Implementation Notes

## 1. Implementation Posture

## 2. Tool-by-tool Setup

### Obsidian

### OmniFocus / Task Manager

### Calendar

## 3. Cadence / Review Rhythm

## 4. Guardrails and Failure Modes

## 5. Metrics and Validation Checks
```

## Rules

- Focus on behaviour, workflows and review loops.
- Do not turn the book into vague inspiration.
- Keep actions concrete.
- Separate "worth remembering" from "worth doing".
- Include citations where specific claims or passages are used.
- Mark output as machine draft unless manually reviewed.
