# Citation and Source Location Support

BookMem stores source-location metadata on every indexed chunk so that agent answers can cite the exact book area used as evidence.

## Stored chunk fields

Each chunk now includes:

```yaml
source_path: data/books/158-applied-psychology-and-self-improvement/Book.md
heading_path: Chapter 6 > Goals Versus Systems
chapter_id: chapter_6
chapter_title: Chapter 6
section_id: chapter_6_goals_versus_systems
section_title: Goals Versus Systems
start_line: 1240
end_line: 1288
citation: Book Title — Author — Chapter 6 > Goals Versus Systems — lines 1240-1288 — data/books/...
```

The line numbers refer to the canonical cleaned Markdown file under `data/books/`, after YAML frontmatter has been removed for indexing. This keeps citations stable for the actual text Sandy reads.

## Displayed search output

Search and routed search results now include a source location and a reusable citation string:

```text
How to Fail at Almost Everything and Still Win Big
Scott Adams
158 — Applied psychology and self-improvement
Chapter 6 > Goals Versus Systems
How to Fail at Almost Everything and Still Win Big — Scott Adams — Chapter 6 · Goals Versus Systems · lines 1240-1288 — data/books/...

chunk_id: scott_adams_how_to_fail...::chunk_000042
citation: *How to Fail at Almost Everything and Still Win Big*; Scott Adams; Chapter 6 > Goals Versus Systems; lines 1240-1288; chunk `...`; data/books/...
```

## Reading tools

The following commands expose line ranges and citations:

```bash
bookmem search "systems versus goals"
bookmem ask-search "What do my books say about systems versus goals?"
bookmem read-around "<chunk_id>" --before 2 --after 3
bookmem read-section --chunk-id "<chunk_id>"
bookmem read-chapter --book "<book_id>" --chapter "Chapter 6"
```

## Agent guidance

When Sandy answers from BookMem, it should:

1. Search or route-search first.
2. Read around the strongest chunk if needed.
3. Cite the book title, author, heading path, line range and chunk ID.
4. Avoid claiming that a book says something unless the cited retrieved text supports it.

A suitable answer citation format is:

```text
Source: *Book Title*; Author; Chapter / section; lines 1240-1288; chunk `book_id::chunk_000042`.
```

## Re-indexing requirement

Because the LanceDB schema now includes new citation fields, run a full reset once after upgrading:

```bash
bookmem ingest --reset
```

After that, normal changed-file indexing can be used:

```bash
bookmem ingest --changed-only
```
