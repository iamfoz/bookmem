# Cleaning Profiles

BookMem supports configurable cleaning profiles for Markdown book cleanup.

Different book sources need different cleaning behaviour. An EPUB/Pandoc
conversion often needs aggressive cleanup. A hand-authored Markdown file may
only need light normalisation. A quotation-heavy book may need blockquotes
preserved carefully.

## Commands

List profiles:

```bash
bookmem cleaning-profiles
```

Validate profile YAML:

```bash
bookmem validate-cleaning-profiles
```

Clean one book with a profile:

```bash
bookmem clean "Book.md" --profile epub_pandoc --output "Book.cleaned.md"
```

Clean in place:

```bash
bookmem clean "Book.md" --profile light_markdown --in-place
```

Clean a directory:

```bash
bookmem clean-books data/raw-books data/books --profile epub_pandoc
```

Prepare books with a specific cleaning profile:

```bash
bookmem prepare-books data/raw-books --profile epub_pandoc --changed-only
```

## Configuration files

Built-in profiles are defined in:

```text
config/cleaning_profiles.yaml
```

Local/custom profiles can be added under:

```text
config/cleaning_profiles.d/
```

Files in `cleaning_profiles.d/` override or extend the base profiles.

## Built-in profiles

### `epub_pandoc`

Aggressive cleanup for EPUB-to-Markdown or Pandoc conversions.

Good for files containing:

```text
image references
SVG wrappers
raw HTML
Pandoc spans
empty anchors
EPUB-generated IDs
hard-wrapped paragraphs
cover/copyright/catalogue clutter before the first chapter/preface
```

Example:

```bash
bookmem clean "Book.md" --profile epub_pandoc
```

### `light_markdown`

Lighter cleanup for Markdown that is already mostly usable.

This keeps images and avoids aggressive paragraph/headings normalisation.

```bash
bookmem clean "Book.md" --profile light_markdown
```

### `preserve_quotes`

Similar to `epub_pandoc`, but more careful about quote/list structure.

```bash
bookmem clean "Book.md" --profile preserve_quotes
```

### `minimal`

Minimal normalisation for hand-authored Markdown.

```bash
bookmem clean "Book.md" --profile minimal
```

## Profile example

```yaml
cleaning_profiles:
  my_custom_profile:
    extends: epub_pandoc
    label: My custom profile
    description: Keep images but remove Pandoc clutter.
    remove_images: false
    remove_html: true
    strip_spans: true
    strip_pandoc_attributes: true
    join_wrapped_lines: true
    normalise_headings: true
```

## Supported options

```yaml
drop_pre_content_matter: true
remove_images: true
remove_html: true
remove_raw_html_blocks: true
remove_empty_anchors: true
remove_div_fences: true
strip_spans: true
strip_pandoc_attributes: true
remove_footnote_links: true
strip_link_targets: true
remove_horizontal_rules: true
remove_idgen_lines: true
normalise_inline_noise: true
join_wrapped_lines: true
normalise_headings: true
remove_blockquotes: false
preserve_lists: true
```

## Inheritance

Profiles can inherit from another profile using `extends`.

```yaml
cleaning_profiles:
  keep_images_epub:
    extends: epub_pandoc
    remove_images: false
```

## Relationship to clean-check

Use cleaning profiles to transform Markdown:

```bash
bookmem clean "Book.md" --profile epub_pandoc --output "Book.cleaned.md"
```

Use clean-check to audit the result:

```bash
bookmem clean-check "Book.cleaned.md"
```

A good workflow is:

```bash
bookmem clean "raw.md" --profile epub_pandoc --output "cleaned.md"
bookmem clean-check "cleaned.md"
bookmem frontmatter generate "cleaned.md" --write
bookmem ingest --changed-only
```
