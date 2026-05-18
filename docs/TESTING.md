# Testing

BookMem includes a pytest suite and a tiny fixture corpus.

The tests are intentionally focused on the parts of the project that are
most likely to break during development:

```text
cleaning
cleaning profiles
clean-check reports
frontmatter generation
ISBN detection
BMDC classification
manifest records
duplicate detection
citation line ranges
reference exports
```

## Install test dependencies

```bash
pip install -e ".[dev]"
```

## Run all tests

```bash
pytest
```

## Run one test file

```bash
pytest tests/test_cleaning.py
```

## Fixture corpus

Test fixtures live under:

```text
tests/fixtures/
  raw/
  cleaned/
  expected/
```

`raw/` contains deliberately messy Markdown with EPUB/Pandoc-style artefacts.

`cleaned/` contains small canonical Markdown books with YAML frontmatter.

`expected/` contains expected metadata snippets used by tests.

## Why fixtures are small

The fixture corpus is deliberately tiny. It is designed to test behaviour,
not retrieval quality over a large library.

Larger retrieval quality checks should live in a future `eval/` suite.
