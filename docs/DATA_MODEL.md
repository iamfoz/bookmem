# Data Model

## Book frontmatter

Canonical books use YAML frontmatter:

```yaml
book_id: atomic_habits_james_clear
title: Atomic Habits
author: James Clear
isbn:
  filename: "9780735211292"
classification:
  primary_class: "158"
  primary_label: Applied psychology and self-improvement
  source: filename_or_classifier
  topics:
    - habits
    - systems
reading:
  difficulty: beginner
  estimated_pages: 320
  estimated_reading_hours: 8
  density: medium
  best_read_as: cover_to_cover
```

## Chunks

Chunks are stored in LanceDB with fields such as:

```text
chunk_id
book_id
title
author
text
source_path
start_line
end_line
heading_path
previous_chunk_id
next_chunk_id
chapter_id
section_id
vector
```

## Summaries

```text
data/summaries/<book_id>/book.yaml
data/summaries/<book_id>/chapters.yaml
```

## Concepts

Concepts are reusable models/frameworks:

```yaml
name: Circle of Influence
type: model
aliases:
  - influence circle
description: ...
source_chunks:
  - ...
review_status: machine_draft
```

## Claims

Claims are assertions:

```yaml
claim: Goals are less useful than systems for long-term success.
stance: supports
confidence: medium
source_chunks:
  - ...
review_status: machine_draft
```

## Passages

Passages support a commonplace-book workflow:

```yaml
quote: ...
summary: ...
why_it_matters: ...
source_chunk: ...
citation: ...
tags:
  - energy management
review_status: machine_draft
```

## Review status

Common statuses:

```text
machine_draft
needs_human_review
human_reviewed
rejected
superseded
```
