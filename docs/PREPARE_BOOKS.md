# Preparing books automatically

BookMem can take messy Markdown exports and turn them into canonical, indexable book files.

The prepare workflow can:

1. clean EPUB/Pandoc/PDF conversion clutter;
2. infer title, author and ISBN from filename when available;
3. scan the Markdown body for checksum-valid ISBNs when filename metadata is poor;
4. optionally enrich the record from the Library of Congress by ISBN;
5. generate YAML frontmatter;
6. choose a BMDC class;
7. rename the file using BookMem's canonical filename format;
8. place it into the appropriate BMDC class folder.

## Canonical layout

Raw exports stay untouched by default:

```text
data/raw-books/
  ugly_export_001.md
```

Prepared books are stored as cleaned Markdown with frontmatter:

```text
data/books/
  158-applied-psychology-and-self-improvement/
    How to Fail at Almost Everything and Still Win Big, Second Edition - Scott Adams - 9798988534969.md
```

## Prepare one book

```bash
bookmem prepare-book "data/raw-books/ugly_export_001.md"
```

With Library of Congress enrichment:

```bash
bookmem prepare-book "data/raw-books/ugly_export_001.md" --enrich-loc
```

If the file is already cleaned and only needs frontmatter/renaming/placement:

```bash
bookmem prepare-book "data/books/unclassified/Book.md" --no-clean
```

## Prepare a whole directory

```bash
bookmem prepare-books data/raw-books
```

With LoC enrichment:

```bash
bookmem prepare-books data/raw-books --enrich-loc
```

## Overwrite behaviour

BookMem is conservative by default.

- It will not overwrite an existing canonical file unless `--overwrite-file` is supplied.
- It will not regenerate existing frontmatter unless `--overwrite-frontmatter` is supplied.
- It will not delete the raw source unless `--delete-source` is supplied.

## Classification behaviour

The prepare workflow uses the same classification priority as frontmatter generation:

1. existing manual frontmatter;
2. optional Library of Congress ISBN class number;
3. folder/path classification;
4. filename, headings and early body text;
5. `999` unclassified.

The final folder is based on the root three-digit BMDC class. For example, `158.1` is placed under the `158-...` folder.

## Canonical filename format

Prepared books use:

```text
<Title> - <Author> - <ISBN>.md
```

If author or ISBN is unavailable, BookMem omits that part rather than inventing data.
