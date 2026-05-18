# Library of Congress enrichment

BookMem can optionally enrich book frontmatter using the Library of Congress catalogue via its public SRU interface.

This is an online, optional step. Normal cleaning, frontmatter generation, and indexing remain local and deterministic.

## Why this exists

Many Markdown books are named using this convention:

```text
<Title> - <Author> - <ISBN>.md
```

BookMem can parse the ISBN from the filename, query the Library of Congress catalogue, and extract a catalogue class number when the returned MARC record contains one.

BookMem stores the resulting number as a BMDC class number. BMDC uses number-compatible routing identifiers, but keeps its own labels, aliases, notes, and documentation text.

## Commands

Look up one ISBN without touching any files:

```bash
bookmem loc-lookup 9798988534969
```

Enrich one cleaned Markdown book:

```bash
bookmem enrich-loc "data/books/158-applied-psychology-personal-development/Book.md"
```

Write the enrichment into frontmatter:

```bash
bookmem enrich-loc "data/books/158-applied-psychology-personal-development/Book.md" --write
```

Bulk enrichment:

```bash
bookmem enrich-loc-books data/books --write
```

## Classification overwrite behaviour

By default, BookMem is conservative.

It will use an LoC class number when the book is unclassified or only auto-classified. It will not replace a manually reviewed classification unless you explicitly ask it to:

```bash
bookmem enrich-loc "data/books/Book.md" --write --overwrite-classification
```

## Stored frontmatter

A successful enrichment adds source data under:

```yaml
classification:
  external:
    library_of_congress:
      source: library_of_congress_sru
      lookup: isbn
      isbn: "9798988534969"
      matched_title: "..."
      matched_author: "..."
      lccn: "..."
      record_count: 1
      class_source_field: "082$a"
      raw_classification_number: "158.1"
      normalised_class_number: "158.1"
      source_url: "https://lx2.loc.gov/sru/lcdb?..."
```

If the LoC class number is applied as BookMem's primary class, the metadata block is also updated:

```yaml
metadata:
  classification_source: library_of_congress_sru_isbn
  classification_review_required: true
```

`classification_review_required` is deliberately set to `true`. Catalogue records are useful, but a human should still review edge cases.

## Field extraction

BookMem currently reads these MARC fields:

| MARC field | Purpose |
|---|---|
| `245$a`, `245$b` | Matched title |
| `100$a`, `700$a` | Matched author |
| `082$a` | Preferred class number |
| `083$a` | Additional class number fallback |
| `010$a`, `001` | Record identifiers |

## Failure behaviour

If no ISBN is present, no catalogue record is found, the service is unavailable, or the record lacks a class number, BookMem leaves existing frontmatter intact.

The normal fallback chain remains:

```text
1. Existing manually reviewed frontmatter
2. Library of Congress ISBN enrichment, if available
3. Folder classification
4. Filename/content classifier
5. 999 unclassified
```
