# Topic maps

Topic maps help BookMem reason across the library before an agent commits to reading full passages.

Chunk search is useful when you already know what you are looking for. Topic mapping is useful when the question is broader, for example:

```bash
bookmem map-topic "systems thinking"
bookmem map-topic "compound interest"
bookmem map-topic "energy management and productivity"
```

A topic map combines:

1. deterministic query routing,
2. book-level and chapter-level summaries,
3. indexed chunk retrieval, where an index is available,
4. repeated terms and phrases from the strongest matches.

The output is designed for agent planning. It tells the agent which books are probably worth reading first, why they matched, and which themes appear repeatedly.

## Basic usage

```bash
bookmem map-topic "systems thinking"
```

Typical output includes:

```text
Topic route
Aliases: productivity, psychology
Classes: 158, 153, 650
Confidence: 0.72

Strongest books:
1. How to Fail at Almost Everything and Still Win Big
2. Atomic Habits
3. Thinking in Systems

Common themes:
- systems over goals
- feedback loops
- habit design
- compounding effects
```

## JSON and YAML output

For agent workflows, use JSON:

```bash
bookmem map-topic "systems thinking" --json
```

To save a map:

```bash
bookmem map-topic "systems thinking" --output exports/topic-maps/systems-thinking.yaml
bookmem map-topic "systems thinking" --output exports/topic-maps/systems-thinking.json --json
```

YAML is used unless the output path ends in `.json`.

## Options

```bash
bookmem map-topic "systems thinking" \
  --book-limit 8 \
  --summary-limit 12 \
  --chunk-limit 12 \
  --themes-limit 12
```

Use summaries only:

```bash
bookmem map-topic "systems thinking" --no-chunks
```

Disable broad fallback after routed chunk search:

```bash
bookmem map-topic "systems thinking" --no-fallback
```

## Recommended workflow

Generate summaries and index the library first:

```bash
bookmem summarise-books data/books
bookmem ingest --changed-only
bookmem map-topic "systems thinking"
```

If summaries are missing, topic maps will be weaker. If the LanceDB index is missing, BookMem will still attempt a summary-only map.

## Design notes

Topic maps are derived reasoning aids. They are not canonical metadata.

The canonical source remains:

```text
data/books/<class-folder>/<book>.md
```

The summary maps remain derived state:

```text
data/summaries/<book_id>/book.yaml
data/summaries/<book_id>/chapters.yaml
```

The topic map itself can be regenerated at any time.
