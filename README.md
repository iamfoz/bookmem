# BookMem

Current package version: **0.9.0**


BookMem is a local, agent-readable Markdown book corpus.

It ingests Markdown books, classifies them with **BookMem Decimal Classification (BMDC)**, chunks them by Markdown structure, embeds them, stores them in LanceDB, and exposes a CLI that agents can use for targeted retrieval.

The design goal is not merely to search Markdown. The goal is to let an agent search the right part of a book library, read around retrieved passages, and cite where ideas came from.


## Classification and IP notes

BookMem uses **BookMem Decimal Classification (BMDC)** as its internal classification layer. BMDC class numbers are intended to be interoperable with the familiar decimal library classification numbering pattern where useful, while the labels, aliases and documentation in this project remain BookMem's own working descriptions.

The practical rule is: use compatible numbers, use our own words. Do not copy proprietary editorial descriptions, captions, notes, schedules or hierarchy text from external classification manuals into `config/bmdc.yaml` or the documentation.

See [`docs/CLASSIFICATION_IP.md`](docs/CLASSIFICATION_IP.md) for the operating rules.

## Licence

BookMem is licensed under **GPL-3.0-only**. See [`LICENSE`](LICENSE).

## Classification note

BMDC is BookMem's own pragmatic decimal subject map. Its numbers are deliberately chosen to remain compatible with established decimal library classification habits where useful, but BMDC is not named as, affiliated with, endorsed by, or a substitute for any third-party classification product. Its wording and routing aliases are original to this project.

The taxonomy is stored in [`config/bmdc.yaml`](config/bmdc.yaml) and documented in [`docs/TAXONOMY.md`](docs/TAXONOMY.md).

## Current features

- Markdown book ingestion
- YAML frontmatter support
- BMDC classification via `config/bmdc.yaml`
- Folder-based classification fallback
- LanceDB vector storage
- Full-text index creation where supported by the installed LanceDB version
- Hybrid, vector and full-text search modes
- BMDC class and routing alias filters
- Context reading around a retrieved chunk
- CLI-first workflow suitable for agent tools

## Project layout

```text
bookmem/
  bookmem/
    cli.py
    config.py
    chunking.py
    embeddings.py
    ingest.py
    search.py
    taxonomy.py
  config/
    bmdc.yaml
  docs/
    TAXONOMY.md
  data/
    books/
      158-applied-psychology-personal-development/
      332-finance-investing-and-financial-markets/
      999-unclassified/
    lancedb/
    manifests/
  pyproject.toml
  LICENSE
  .env.example
```

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

For development tools:

```bash
pip install -e '.[dev]'
```

## Add books

Place Markdown files under `data/books/`.

Example:

```text
data/books/
  158-applied-psychology-personal-development/
    Atomic Habits - James Clear.md
  332-finance-investing-and-financial-markets/
    The Psychology of Money - Morgan Housel.md
```

BookMem will infer the primary BMDC class from the parent folder if the Markdown file does not contain frontmatter.

## Recommended frontmatter

```yaml
---
title: The Psychology of Money
author: Morgan Housel

classification:
  scheme: bmdc
  primary_class: "332"
  primary_label: Finance, investing and financial markets
  secondary_class:
    - "153"
    - "158"
  routing_aliases:
    - finance
    - investing
    - behavioural_finance
  topics:
    - money psychology
    - investing
    - risk
    - compounding
    - wealth
---
```

A productivity book might look like:

```yaml
---
title: Atomic Habits
author: James Clear

classification:
  scheme: bmdc
  primary_class: "158"
  primary_label: Applied psychology and self-improvement
  secondary_class:
    - "153"
  routing_aliases:
    - personal_development
    - productivity
    - habits
  topics:
    - habit formation
    - behaviour change
    - systems
    - identity
---
```

## Ingest

```bash
bookmem ingest --reset
```

This reads Markdown files, creates chunks, embeds them using the configured sentence-transformers model, stores them in LanceDB, and attempts to create a full-text index on the `text` column.

The first run may take a while because the embedding model needs to be downloaded.

## Search

Search all indexed books:

```bash
bookmem search "compound interest"
```

Search only finance-related material using a routing alias:

```bash
bookmem search "compound interest" --alias finance
```

Search by BMDC class code:

```bash
bookmem search "habit formation" --class 158
```

Use explicit search modes:

```bash
bookmem search "identity-based habits" --mode hybrid
bookmem search "identity-based habits" --mode vector
bookmem search "identity-based habits" --mode fts
```

## Read surrounding context

Search results include a `chunk_id`. Use it to read around a result:

```bash
bookmem read james_clear_atomic_habits::chunk_000012 --context 2
```

## List indexed books

```bash
bookmem list-books
bookmem list-books --class 332
bookmem list-books --alias finance
```

## Inspect taxonomy

```bash
bookmem list-taxonomy
bookmem list-aliases
```

## Agent usage pattern

An agent should use BookMem like this:

```text
1. Classify the user question into likely routing aliases or BMDC classes.
2. Search using `bookmem search` with those filters.
3. Inspect the strongest results.
4. Use `bookmem read` to read neighbouring context.
5. Answer only from retrieved evidence.
6. Broaden the search only if results are weak or the question is cross-domain.
```

Examples:

```bash
bookmem search "what do my books say about market crashes?" --alias finance --limit 8
bookmem search "how do I improve focus?" --alias productivity --limit 8
bookmem search "how should I think about risk?" --alias finance --alias psychology --limit 12
```

## Classification strategy

Every book should have:

- one primary BMDC class
- zero or more secondary BMDC classes
- zero or more routing aliases
- zero or more topic tags

The primary class answers: **where does this book mainly belong?**

The secondary classes and tags answer: **where else might this book be useful?**

The routing aliases answer: **which common agent queries should include this book?**

## Optional Library of Congress enrichment

If your files are named `<Title> - <Author> - <ISBN>.md`, BookMem can use the ISBN to query the Library of Congress SRU catalogue and copy a catalogue class number into the book frontmatter as a BMDC-compatible class identifier.

```bash
bookmem loc-lookup 9798988534969
bookmem enrich-loc "data/books/Book.md" --write
bookmem enrich-loc-books data/books --write
bookmem scan-isbns "data/books/unclassified/Book.md"
```

This is optional and online-only. See `docs/LOC_ENRICHMENT.md`.

## ISBN discovery

BookMem can scan poorly named Markdown exports for checksum-validated ISBNs and use those ISBNs for optional catalogue enrichment. See `docs/ISBN_DISCOVERY.md`.


## Automatic book preparation

Raw Markdown exports can be cleaned, frontmattered, classified, renamed and placed into the canonical BMDC folder structure in one step:

```bash
bookmem prepare-book "data/raw-books/ugly_export_001.md"
bookmem prepare-book "data/raw-books/ugly_export_001.md" --enrich-loc
bookmem prepare-books data/raw-books --enrich-loc
```

Prepared files are stored under `data/books/<class-folder>/` using:

```text
<Title> - <Author> - <ISBN>.md
```

See `docs/PREPARE_BOOKS.md` for the full workflow.

## Manifest and changed-file detection

BookMem stores generated operational state in `data/manifests/books.json`. This lets repeated runs skip unchanged books.

```bash
bookmem status
bookmem prepare-books data/raw-books --changed-only
bookmem ingest --changed-only
```

The manifest tracks body hashes, frontmatter hashes, preparation/index timestamps, chunk counts and classification source. Canonical metadata still lives in each cleaned Markdown file's YAML frontmatter.

See `docs/MANIFEST.md` for details.

## Book and chapter summaries

Generate derived book/chapter summary maps before searching chunks:

```bash
bookmem summarise-books data/books
bookmem search-summaries "systems versus goals"
```

Summaries are stored under `data/summaries/<book_id>/book.yaml` and `data/summaries/<book_id>/chapters.yaml`. They are derived state and can be rebuilt from the cleaned Markdown books. See `docs/SUMMARIES.md`.


## Query routing

BookMem can deterministically route a natural-language question to likely BMDC aliases and class codes before searching.

```bash
bookmem route "What do my books say about compound interest?"
bookmem ask-search "What do my books say about compound interest?"
bookmem ask-search "systems versus goals" --summaries-first
```

The router is rules-based in this version. It uses BMDC aliases, class labels, topic hints and configured routing aliases. It does not call an LLM by default.

See `docs/ROUTER.md`.


## Reading context safely

BookMem stores chapter, section and neighbour metadata for every chunk. This lets agents expand context without dumping an entire book.

```bash
bookmem read "<chunk_id>" --context 2
bookmem read-around "<chunk_id>" --before 2 --after 3
bookmem read-section --chunk-id "<chunk_id>"
bookmem read-chapter --book "<book_id>" --chapter "Chapter 6"
```

See `docs/READING_TOOLS.md` for the agent guidance and metadata details.

## Citation support

BookMem stores source-location metadata on every indexed chunk, including `source_path`, `heading_path`, `chapter_id`, `section_id`, `start_line`, `end_line` and a generated citation string. Search, routed search and reading commands now display line ranges and reusable citations for agent answers.

See [`docs/CITATIONS.md`](docs/CITATIONS.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
