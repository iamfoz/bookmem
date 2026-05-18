# Pluggable citation styles

BookMem citation styles are data-driven YAML definitions. Built-in styles live in:

```text
config/citation_styles.yaml
```

Local or project-specific styles can be added under:

```text
config/citation_styles.d/
```

Files in `citation_styles.d` are loaded after the built-in file, so a local style with the same key overrides the bundled definition.

## Commands

List available styles:

```bash
bookmem citation-styles
```

Validate styles by rendering a sample reference:

```bash
bookmem validate-citation-styles
```

Use a style:

```bash
bookmem cite "data/books/Book.md" --style apa
bookmem cite-books data/books --style harvard --output exports/references-harvard.md
```

## Style file format

A style file contains a `styles` mapping. Each style has a short key, label, description and ordered template parts.

```yaml
styles:
  short:
    label: Short book reference
    description: Author, year and title only.
    parts:
      - template: "{author_display} ({year})."
      - template: "*{title}*."
```

## Available placeholders

```text
{author}
{author_raw}
{author_apa}
{author_display}
{author_family}
{author_given}
{year}
{title}
{edition}
{publisher}
{place}
{isbn}
{book_id}
{primary_class}
```

## Conditional parts

Template parts can be conditional:

```yaml
- template: "{publisher}."
  when: publisher

- template: "{place}: {publisher}."
  all_when: [place, publisher]

- template: "{publisher}."
  all_when: [publisher]
  none_when: [place]
```

Supported conditions:

```text
when: field
all_when: [field, field]
any_when: [field, field]
none_when: [field, field]
```

## Disabled examples

Styles with keys starting with `_` are treated as examples/private drafts and are hidden from normal style listings.

```yaml
styles:
  _example_short:
    label: Example short reference
    parts:
      - template: "{author_display} ({year})."
      - template: "*{title}*."
```

## Scope

This is a practical BookMem citation layer, not a full CSL engine. It is intended for readable book references generated from canonical Markdown frontmatter. For formal academic submission, check final references against the relevant university or journal style guide.

Reference-manager exports such as BibTeX, RIS, CSL JSON and EndNote XML remain code-backed because those are structured interchange formats rather than prose citation styles.
