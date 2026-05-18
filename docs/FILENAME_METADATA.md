# Filename metadata

BookMem supports the following filename convention for raw and cleaned Markdown books:

```text
<Title> - <Author> - <ISBN>.md
```

The ISBN segment is optional:

```text
<Title> - <Author>.md
<Title> - <Author> - <ISBN>.md
```

Examples:

```text
How to Fail at Almost Everything and Still Win Big, Second Edition - Scott Adams - 9798988534969.md
The Psychology of Money - Morgan Housel - 9780857197689.md
Atomic Habits - James Clear - 9781847941831.md
```

## What BookMem extracts

When generating frontmatter, BookMem parses the filename from right to left:

```yaml
title: How to Fail at Almost Everything and Still Win Big, Second Edition
author: Scott Adams
isbn:
  filename: "9798988534969"
```

The parser splits on ` - ` rather than every hyphen, so titles and author names may contain ordinary hyphenated words.

## Classification assistance

Filename metadata is used as one signal when suggesting BMDC classification:

1. Existing frontmatter wins.
2. Folder path wins next, for example `332-finance-investing-and-financial-markets/`.
3. Filename, headings and early body text are used as a conservative automatic suggestion.
4. If no confident signal is found, the book remains `999`.

For example, a title or body mentioning investing, funds, portfolio, markets or wealth will usually suggest:

```yaml
classification:
  primary_class: "332"
```

A title or body mentioning habits, systems, goals, self-improvement or success will usually suggest:

```yaml
classification:
  primary_class: "158"
```

## Important limitation

ISBN is stored as canonical metadata, but BookMem does not yet perform online ISBN lookups by default. This keeps the core workflow local and reproducible.

A future optional command could enrich frontmatter from Open Library, Google Books or another provider, but that should be a separate opt-in feature because online metadata varies in quality and licensing.

## Recommended workflow

```bash
bookmem clean-books data/raw-books data/books
bookmem frontmatter generate-books data/books --write
bookmem frontmatter validate data/books/158-applied-psychology-personal-development/Book.md
bookmem ingest --reset
```

If the generated class is wrong, edit the YAML frontmatter directly. The frontmatter is the canonical source of truth.
