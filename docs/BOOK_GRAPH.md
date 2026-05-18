# Book Relationship Graph

BookMem can build a derived book-to-book relationship graph.

Topic maps are query-focused. The book graph is library-focused: it records
relationships between books so agents can quickly answer, "What else should I
read around this?"

## Derived file

```text
data/graphs/book_graph.json
```

This file is derived state. It can be deleted and rebuilt from canonical
Markdown, frontmatter, summaries and edition metadata.

## Build the graph

```bash
bookmem build-graph
```

Custom output:

```bash
bookmem build-graph --output data/graphs/book_graph.json
```

JSON output:

```bash
bookmem build-graph --json
```

## Find related books

Related to a book/title/author/work:

```bash
bookmem related "Atomic Habits"
```

Related to a topic:

```bash
bookmem related --topic "systems thinking"
```

Rebuild before querying:

```bash
bookmem related "Atomic Habits" --rebuild
```

JSON output:

```bash
bookmem related "Atomic Habits" --json
```

## Relationship signals

The graph currently uses deterministic signals:

```text
same topics
same class
same routing aliases
similar summaries
same author
same work/edition group
```

## Example output

```text
Related books: Atomic Habits

1. How to Fail at Almost Everything and Still Win Big
   Reason: shared topics: systems, habits, productivity

2. The 7 Habits of Highly Effective People
   Reason: same class 158; shared topics: habits, effectiveness
```

## How an assistant agent should use it

Recommended pattern:

```text
1. Use bookmem related for book/topic expansion.
2. Use bookmem map-topic for a broader theme view.
3. Use bookmem search/read-around for supporting passages.
4. Cite chunk sources when making claims.
```

## Rebuild timing

Rebuild the graph after:

```text
adding/removing books
changing topics/routing aliases
generating or updating summaries
changing work/edition metadata
```

Suggested workflow:

```bash
bookmem summarise-books data/books
bookmem editions --write
bookmem build-graph
```
