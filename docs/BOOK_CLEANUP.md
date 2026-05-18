# Markdown Book Cleanup

BookMem works best when the Markdown source is clean reading text, not a direct dump of EPUB layout markup.

Many EPUB-to-Markdown conversions contain noise such as:

- cover image references
- SVG wrappers
- empty HTML anchors
- Pandoc div fences such as `::: {#some-id .class}`
- character style spans such as `[word]{.CharOverride-5}`
- EPUB-generated IDs
- front-matter pages that are useful to a publisher but not useful for retrieval
- hard-wrapped lines that split normal paragraphs

That material can pollute vector search and full-text search because the model sees class names, image paths, anchor IDs and catalogue boilerplate as part of the book.

## Command

Clean one file into a sibling file:

```bash
bookmem clean "data/books/158-applied-psychology-personal-development/Book.md"
```

This writes:

```text
Book.cleaned.md
```

Write to a specific file:

```bash
bookmem clean "Book.md" --output "Book.clean.md"
```

Overwrite the source file:

```bash
bookmem clean "Book.md" --in-place
```

Clean a directory tree into a separate output tree:

```bash
bookmem clean-books data/raw-books data/books
```

## Front matter behaviour

By default, BookMem drops publisher/copyright/catalogue/promo material before the first real content heading it recognises, such as:

- Preface
- Introduction
- Prologue
- Chapter 1

To preserve that material:

```bash
bookmem clean "Book.md" --keep-front-matter
```

## What the cleaner does

The cleaner is deliberately conservative. It aims to remove structural and conversion noise while preserving the author's prose.

It currently:

- removes image references
- removes SVG and raw HTML blocks
- removes empty EPUB anchors
- removes Pandoc div fences
- unwraps Pandoc span attributes while keeping the text
- keeps ordinary link text but removes link targets
- joins hard-wrapped prose into normal Markdown paragraphs
- converts obvious book headings into Markdown headings
- emits a cleanup report

## Recommended workflow

Use a two-stage library:

```text
data/raw-books/     # original converted Markdown, not indexed
data/books/         # cleaned Markdown, indexed by BookMem
```

Then run:

```bash
bookmem clean-books data/raw-books data/books
bookmem ingest --reset
```

This keeps the original conversion output intact while making the indexed corpus cleaner and more stable.

## Important limitation

This tool is not a copyright scrubber, summariser or paraphraser. It keeps the author's text intact where possible. Its job is to remove conversion noise before indexing.
