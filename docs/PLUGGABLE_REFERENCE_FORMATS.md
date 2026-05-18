# Pluggable reference export formats

BookMem reference export formats are YAML-defined.

Built-in formats live in:

```text
config/reference_export_formats.yaml
```

Local formats can be added under:

```text
config/reference_export_formats.d/
```

Files in `reference_export_formats.d/` are loaded after the built-in file. If a local file uses the same format key as a built-in format, the local definition overrides the built-in one.

## Commands

List available formats:

```bash
bookmem reference-formats
```

Validate all configured formats:

```bash
bookmem validate-reference-formats
```

Export references:

```bash
bookmem export-references data/books --format bibtex --output exports/references.bib
bookmem export-references data/books --format ris --output exports/references.ris
bookmem export-references data/books --format csl-json --output exports/references.json
bookmem export-references data/books --format endnote-xml --output exports/references.xml
```

## Built-in engines

BookMem currently supports three export engines.

### `text_records`

Use this for line-based formats such as BibTeX, RIS, TSV, CSV-like text, Markdown bibliographies or plain text exchange files.

```yaml
formats:
  simple-tsv:
    label: Simple TSV
    description: One tab-separated record per book.
    extension: tsv
    media_type: text/tab-separated-values
    engine: text_records
    record_separator: "\n"
    record:
      fields:
        - template: "{author_raw}\t{year_raw}\t{title}\t{isbn}\t{book_id}"
```

### `json_records`

Use this for JSON formats where each book becomes one object in a list.

```yaml
formats:
  minimal-json:
    label: Minimal JSON
    extension: json
    media_type: application/json
    engine: json_records
    indent: 2
    fields:
      - key: id
        source: book_id
      - key: title
        source: title
      - key: author
        source: author_raw
        when: author
```

### `xml_records`

Use this for simple XML formats where each book becomes a repeated record element.

```yaml
formats:
  simple-xml:
    label: Simple XML
    extension: xml
    media_type: application/xml
    engine: xml_records
    root: books
    records_path: records
    record_element: book
    fields:
      - path: title
        source: title
      - path: author
        source: author_raw
        when: author
```

## Conditions

Fields support the same simple conditions as citation styles:

```yaml
when: isbn
all_when:
  - author
  - title
any_when:
  - isbn
  - publisher
none_when:
  - edition
```

## Available placeholders and sources

Common values include:

```text
author
author_raw
author_apa
author_display
author_family
author_given
year
year_raw
title
title_raw
edition
publisher
place
isbn
book_id
primary_class
primary_label
source_path
bibtex_key
title_bibtex
author_bibtex
publisher_bibtex
place_bibtex
edition_bibtex
isbn_bibtex
book_id_bibtex
author_csl
issued_csl
categories_csl
```

For `text_records`, use `template`.

For `json_records` and `xml_records`, use `source`, `literal` or `template`.

## Design note

Reference export formats are operational serialisation rules. They are not canonical metadata. The canonical book metadata remains the YAML frontmatter in each cleaned Markdown book.
