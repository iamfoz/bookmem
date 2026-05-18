# Reading and Context Expansion Tools

BookMem stores navigation metadata for every indexed chunk so agents can safely expand context without reading an entire book.

## Chunk navigation metadata

During ingest, each chunk now stores:

```yaml
chapter_id: chapter_6
chapter_title: Chapter 6
section_id: chapter_6_goals_versus_systems
section_title: Goals Versus Systems
previous_chunk_id: scott_adams_how_to_fail...::chunk_000041
next_chunk_id: scott_adams_how_to_fail...::chunk_000043
```

The IDs are generated from Markdown headings. Explicit headings such as `Chapter 6`, `Preface`, `Introduction`, `Conclusion`, `Afterword` and `Appendix` are treated as chapter-level containers. If a book does not use explicit chapter names, the highest-level heading is used as the chapter container.

## Commands

### Read equal context either side

```bash
bookmem read "<chunk_id>" --context 2
```

This is the original read behaviour, now backed by the richer navigation metadata.

### Read different amounts before and after

```bash
bookmem read-around "<chunk_id>" --before 2 --after 3
```

This is the preferred tool for agents when they need a little more context around a search result.

### Read the whole section containing a chunk

```bash
bookmem read-section --chunk-id "<chunk_id>"
```

Use this when the search result appears to be in the middle of a coherent section and the agent needs the full local argument.

### Read a chapter

```bash
bookmem read-chapter --book "<book_id>" --chapter "Chapter 6"
```

The `--book` value can be either the indexed `book_id` or the exact book title.

## Agent guidance

Recommended agent flow:

```text
search or ask-search
→ inspect top results
→ read-around strongest chunk
→ read-section if the local argument is incomplete
→ read-chapter only when the question needs chapter-level context
```

Do not read whole chapters by default. Use chapter reading when a passage clearly depends on a wider argument or when the user specifically asks for chapter-level coverage.

## Reindex required

Because these fields are stored in the LanceDB chunk table, run a reset ingest after upgrading:

```bash
bookmem ingest --reset
```

After that, `bookmem ingest --changed-only` can be used as normal.
