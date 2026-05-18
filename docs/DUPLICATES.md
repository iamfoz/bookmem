# Duplicate Detection

BookMem includes a duplicate detector for canonical books and, optionally, raw Markdown exports.

Duplicates can happen when you import the same book twice, keep several editions, re-download an EPUB conversion, or have both a raw export and a cleaned canonical copy.

## Commands

```bash
bookmem duplicates
bookmem duplicates --by isbn
bookmem duplicates --by title-author
bookmem duplicates --by content
bookmem duplicates --by near
bookmem duplicates --write-review
```

By default, `bookmem duplicates` scans the configured canonical books directory and also includes `data/raw-books/` when it exists.

Use this to scan only canonical books:

```bash
bookmem duplicates --canonical-only
```

Use a custom raw directory:

```bash
bookmem duplicates --raw-dir /path/to/raw-books
```

## Detection methods

### ISBN

Flags books sharing the same checksum-valid ISBN.

This is the strongest normal duplicate signal, but it can also indicate different exports of the same edition.

```bash
bookmem duplicates --by isbn
```

### Normalised title and author

Normalises punctuation, articles and edition words before comparing title and author.

```bash
bookmem duplicates --by title-author
```

This catches cases where ISBN is missing but the book metadata is otherwise clear.

### Content hash

Computes a normalised body hash after stripping frontmatter and normalising whitespace.

```bash
bookmem duplicates --by content
```

This catches exact or nearly exact re-exports where filenames or frontmatter differ.

### Near-duplicate similarity

Uses fuzzy title/author comparison and a body fingerprint to catch likely duplicates that do not share an ISBN or exact hash.

```bash
bookmem duplicates --by near --threshold 0.88
```

Lower thresholds find more possible duplicates but produce more noise.

## Review file

You can write duplicate results to:

```text
data/review/possible_duplicates.yaml
```

Run:

```bash
bookmem duplicates --write-review
bookmem review duplicates
bookmem review duplicates --regenerate
```

The review file is deliberately non-destructive. It does not delete, rename or move files. It gives you a structured list to review.

Each group includes:

```yaml
reason: same ISBN
score: 1.0
review:
  status: pending
  action: null
  notes: null
books:
  - path: data/books/158.../Atomic Habits - James Clear.md
    title: Atomic Habits
    author: James Clear
    isbns:
      - "9780735211292"
```

## What BookMem does not do automatically

BookMem does not automatically delete duplicates. That would be reckless.

Different editions, translations, audiobook-derived transcripts and annotated copies may legitimately share a title or even an ISBN-like source trail. The duplicate detector flags candidates. You decide what to keep.
