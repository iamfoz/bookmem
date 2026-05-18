# ISBN Discovery

BookMem can infer book metadata even when filenames do not follow the preferred
`<Title> - <Author> - <ISBN>.md` convention.

The discovery order is:

1. Existing YAML frontmatter.
2. Filename parsing, if the filename follows a useful pattern.
3. Checksum-validated ISBNs found inside the Markdown body.
4. Optional Library of Congress SRU lookup using the discovered ISBN.
5. Folder/path classification and BookMem's local keyword classifier as fallbacks.

## Why ISBN scanning matters

Many Markdown books exported from EPUB or PDF contain a copyright or catalogue
page near the front of the file. That page often contains one or more ISBNs. If
BookMem can find one, it can use the ISBN as a high-confidence key for catalogue
enrichment.

## Scanning a file

```bash
bookmem scan-isbns "data/books/unclassified/Some badly named export.md"
```

## Generating frontmatter from a poorly named file

```bash
bookmem frontmatter generate "data/books/unclassified/Some badly named export.md" --write
```

If an ISBN is found in the book text, BookMem stores it under `isbn` and records
all discovered ISBNs in `metadata.detected_text_isbns`.

## Enriching from the Library of Congress

```bash
bookmem enrich-loc "data/books/unclassified/Some badly named export.md" --write
```

Bulk workflow:

```bash
bookmem frontmatter generate-books data/books --write
bookmem enrich-loc-books data/books --write
```

## False-positive control

BookMem validates ISBN check digits before accepting a candidate. It accepts bare
ISBN-13 values because they are distinctive (`978` or `979`). Bare ISBN-10 values
are accepted only when the nearby text explicitly mentions ISBN, because random
catalogue fragments and image dimensions can otherwise look like valid ISBN-10s.

## Important note

ISBN discovery is a metadata aid, not a substitute for human review. A single
book can contain multiple ISBNs for hardback, paperback, ebook and audiobook
editions. Any of them may be good enough for catalogue lookup, but reviewed
frontmatter remains the canonical metadata source.
