# Reading Lists

BookMem can generate ordered reading lists from the corpus.

This is not just a ranked search result. The generator uses:

```text
routing
passage search
summaries
concepts
topic maps
book graph relationships
class metadata
```

## Commands

General request:

```bash
bookmem reading-list "I want to understand habit design"
```

Topic:

```bash
bookmem reading-list --topic "personal finance for beginners"
```

Goal:

```bash
bookmem reading-list --goal "build an executive assistant agent"
```

Limit number of books:

```bash
bookmem reading-list --topic "systems thinking" --limit 5
```

Save output:

```bash
bookmem reading-list --topic "habit design" --save --name habit-design
```

JSON output:

```bash
bookmem reading-list --goal "understand investing" --json
```

## Saved files

Saved reading lists are written to:

```text
data/reading-lists/
  habit-design.json
  habit-design.md
```

## Output

Example:

```text
1. Start here: Atomic Habits
   Why: foundational habit design and environment shaping

2. Then read: How to Fail at Almost Everything and Still Win Big
   Why: systems over goals, skill stacking and energy management

3. Read after the foundations: The Fifth Discipline
   Why: broader systems thinking and feedback loops
```

Each item includes:

```text
rank
title
author
book_id
class
why
evidence
suggested posture
source path
```

## Suggested postures

The generator can label items as:

```text
Start here
Read early
Then read
Read after the foundations
Use as a reference
```

## Evidence

Evidence can come from:

```text
citations
heading paths
concept matches
summary matches
topic-map matches
graph relationships
```

## Audit

Reading-list generation writes audit records:

```text
reading_list.generate
```

## Future improvement

Once reading metadata exists, the generator can also account for:

```text
difficulty
estimated length
density
best read as cover-to-cover/reference/skim
```


## Reading metadata integration

When available, reading lists use frontmatter reading metadata:

```yaml
reading:
  difficulty: beginner
  estimated_pages: 312
  estimated_reading_hours: 8
  density: medium
  best_read_as: cover_to_cover
```

This improves suggested reading posture and adds length/difficulty context
to saved Markdown lists.
