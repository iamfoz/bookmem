# Clean Check

`bookmem clean-check` audits a cleaned Markdown book before it is indexed.

The cleaner is deliberately separate from the checker:

```text
clean       changes text
clean-check audits text
```

This helps prevent EPUB/Pandoc export clutter from polluting LanceDB search,
topic maps, notes and agent answers.

## Command

```bash
bookmem clean-check "data/books/158.../Book.md"
```

JSON output:

```bash
bookmem clean-check "data/books/158.../Book.md" --json
```

CI-friendly failure modes:

```bash
bookmem clean-check "Book.md" --fail-on-warning
bookmem clean-check "Book.md" --fail-on-fail
```

## Checks

The report includes:

```text
Images remaining
HTML tags remaining
SVG/raw image tags remaining
Pandoc spans remaining
Pandoc attributes remaining
Pandoc div fences remaining
Empty anchors remaining
Raw HTML fences remaining
EPUB artefact markers
Footnote backlink artefacts
Non-breaking spaces
Hard-wrap splits
Average paragraph length
Heading structure
ISBNs found
Frontmatter present/missing
```

## Example report

```text
Images remaining: 0
HTML tags remaining: 0
Pandoc spans remaining: 0
Empty anchors remaining: 0
Average paragraph length: OK
Heading structure: OK
ISBNs found: 4
Frontmatter: present
```

## Status levels

```text
OK    no meaningful issue found
WARN  review recommended
FAIL  likely unsuitable for indexing without cleanup
```

## Why paragraph length matters

Very long paragraphs often mean the export is still hard-wrapped,
poorly separated, or missing headings. That makes chunking weaker and can
produce retrieval results that are too broad.

## Why heading structure matters

BookMem uses headings to identify chapters and sections. If headings are
missing or deeply nested from the start, chapter-aware reading commands such
as `read-chapter` and `read-section` will be less reliable.

## Recommended preparation flow

```bash
bookmem prepare-books data/raw-books --changed-only
bookmem clean-check "data/books/.../Book.md"
bookmem frontmatter validate "data/books/.../Book.md"
bookmem ingest --changed-only
```

## Machine-readable output

Use `--json` for review queues, CI, or external automation:

```bash
bookmem clean-check "Book.md" --json
```

The JSON contains full check counts, status values, ISBNs, frontmatter
information, heading diagnostics, paragraph diagnostics and recommendations.
