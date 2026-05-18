# Reference exports and formatted citations

BookMem can generate human-readable book citations and export references for common reference managers.

This layer uses the canonical Markdown frontmatter as its source of truth. It does not use LanceDB and it does not read chunk text.

## Supported formatted citation styles

BookMem currently supports pragmatic book-reference output for:

- `apa`
- `harvard`
- `mla`
- `chicago`

These are intended as useful working citations for notes, essays, bibliographies and agent output. University departments can vary in their exact Harvard/Chicago/MLA/APA expectations, so final academic submissions should still be checked against the relevant institutional style guide.

## Supported reference manager exports

BookMem can export:

- `bibtex` for BibTeX-compatible tools
- `ris` for Zotero, Mendeley, EndNote and many library tools
- `csl-json` for CSL-compatible processors
- `endnote-xml` for EndNote-style XML import workflows

## Frontmatter fields used

BookMem reads these fields when available:

```yaml
title: The Psychology of Money
subtitle: Timeless Lessons on Wealth, Greed, and Happiness
author: Morgan Housel
year: "2020"
publisher: Harriman House
place: Petersfield
edition: 1st ed.
isbn:
  filename: "9780857197689"
classification:
  primary_class: "332"
  primary_label: Finance, investing and financial markets
```

Equivalent nested publication fields are also supported:

```yaml
publication:
  year: "2020"
  publisher: Harriman House
  place: Petersfield
  edition: 1st ed.
```

## Generate one citation

```bash
bookmem cite "data/books/332-finance-investing-and-financial-markets/The Psychology of Money - Morgan Housel - 9780857197689.md" --style apa
bookmem cite "data/books/332-finance-investing-and-financial-markets/The Psychology of Money - Morgan Housel - 9780857197689.md" --style harvard
bookmem cite "data/books/332-finance-investing-and-financial-markets/The Psychology of Money - Morgan Housel - 9780857197689.md" --style mla
bookmem cite "data/books/332-finance-investing-and-financial-markets/The Psychology of Money - Morgan Housel - 9780857197689.md" --style chicago
```

## Generate citations for the whole library

```bash
bookmem cite-books data/books --style apa
bookmem cite-books data/books --style harvard --output exports/references-harvard.md
```

## Export references

```bash
bookmem export-references data/books --format bibtex --output exports/references.bib
bookmem export-references data/books --format ris --output exports/references.ris
bookmem export-references data/books --format csl-json --output exports/references.json
bookmem export-references data/books --format endnote-xml --output exports/references.xml
```

## Recommended workflow

```bash
bookmem prepare-books data/raw-books --enrich-loc --changed-only
bookmem review
bookmem review apply
bookmem cite-books data/books --style harvard --output exports/references-harvard.md
bookmem export-references data/books --format ris --output exports/references.ris
```

## Notes

- The export layer uses book-level metadata only.
- Passage citations still come from indexed chunk metadata and line ranges.
- Reference-manager exports are useful for managing the books as sources.
- Chunk citations are useful when an agent quotes or relies on a specific passage.
