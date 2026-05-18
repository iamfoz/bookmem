# BookMem

Current package version: **0.17.0**


BookMem is a local, agent-readable Markdown book corpus.

It ingests Markdown books, classifies them with **BookMem Decimal Classification (BMDC)**, chunks them by Markdown structure, embeds them, stores them in LanceDB, and exposes a CLI that agents can use for targeted retrieval.

The design goal is not merely to search Markdown. The goal is to let an agent search the right part of a book library, read around retrieved passages, and cite where ideas came from.


## Classification and IP notes

BookMem uses **BookMem Decimal Classification (BMDC)** as its internal classification layer. BMDC class numbers are intended to be interoperable with the familiar decimal library classification numbering pattern where useful, while the labels, aliases and documentation in this project remain BookMem's own working descriptions.

The practical rule is: use compatible numbers, use our own words. Do not copy proprietary editorial descriptions, captions, notes, schedules or hierarchy text from external classification manuals into `config/bmdc.yaml` or the documentation.

See [`docs/CLASSIFICATION_IP.md`](docs/CLASSIFICATION_IP.md) for the operating rules.

## Licence

BookMem is licensed under **GPL-3.0-only**. See [`LICENSE`](LICENSE).

## Author

BookMem was created by **Martyn Forryan**.

See [`AUTHORS.md`](AUTHORS.md) and [`NOTICE`](NOTICE).


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
- Review queue for metadata, classification, ISBN conflicts and low-confidence matches
- Formatted citations and pluggable reference manager exports
- Collection-level statistics by class, author and topic
- CLI-first workflow suitable for agent tools
- Portable exports for Sandy, OpenClaw, Claude Code, LlamaIndex and LangChain

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

## Duplicate detection

Find duplicate and near-duplicate books before indexing or tidying the library:

```bash
bookmem duplicates
bookmem duplicates --by isbn
bookmem duplicates --by title-author
bookmem duplicates --by content
bookmem duplicates --by near
bookmem duplicates --write-review
```

See `docs/DUPLICATES.md`.

## Collection statistics

Inspect the shape and balance of the canonical library:

```bash
bookmem stats
bookmem stats --by-class
bookmem stats --by-author
bookmem stats --by-topic
bookmem stats --json
```

See `docs/STATS.md`.

## Topic maps

Build an agent-friendly map of a topic across summaries and indexed chunks:

```bash
bookmem map-topic "systems thinking"
bookmem map-topic "compound interest" --json
bookmem map-topic "energy management" --output exports/topic-maps/energy-management.yaml
```

Topic maps show likely BMDC routing, strongest books, recurring themes and evidence snippets so an agent can decide what to read next.

See `docs/TOPIC_MAPS.md`.

## Agent exports

BookMem can export the corpus for other agents and retrieval frameworks. See [`docs/AGENT_EXPORTS.md`](docs/AGENT_EXPORTS.md).

```bash
bookmem export --format jsonl
bookmem export --format llamaindex
bookmem export --format langchain
bookmem export --format markdown-index
bookmem export --format all
```

Useful output files include:

```text
exports/bookmem_chunks.jsonl
exports/bookmem_books.json
exports/bookmem_agent_tools.md
```

## Reference exports

BookMem can generate formatted book citations and export reference-manager files from canonical Markdown frontmatter.

```bash
bookmem cite "data/books/Book.md" --style apa
bookmem cite-books data/books --style harvard --output exports/references-harvard.md
bookmem export-references data/books --format bibtex --output exports/references.bib
bookmem export-references data/books --format ris --output exports/references.ris
bookmem export-references data/books --format csl-json --output exports/references.json
bookmem export-references data/books --format endnote-xml --output exports/references.xml
```

Supported formatted styles are `apa`, `harvard`, `mla` and `chicago`. Supported export formats are `bibtex`, `ris`, `csl-json` and `endnote-xml`.

See [`docs/REFERENCE_EXPORTS.md`](docs/REFERENCE_EXPORTS.md).

## Review queue

Automatic metadata extraction and classification are useful, but they should not be treated as infallible. BookMem can generate a review queue under:

```text
data/review/
  needs_metadata.yaml
  needs_classification.yaml
  low_confidence_matches.yaml
```

Generate the queue:

```bash
bookmem review
```

Inspect specific queues:

```bash
bookmem review metadata
bookmem review classifications
bookmem review isbn-conflicts
bookmem review low-confidence
```

To apply edits, mark entries in the YAML as approved and set the relevant reviewed fields, then run:

```bash
bookmem review apply
```

Review application updates Markdown frontmatter only. It does not silently delete files or move books around.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.


## Pluggable citation styles

BookMem citation styles are YAML-defined. Built-in styles live in `config/citation_styles.yaml`, and local styles can be added under `config/citation_styles.d/`.

```bash
bookmem citation-styles
bookmem validate-citation-styles
bookmem cite "data/books/Book.md" --style apa
```

See `docs/PLUGGABLE_CITATIONS.md` for the template format.

## Pluggable reference export formats

BookMem reference export formats are YAML-defined.
Built-in export formats live in `config/reference_export_formats.yaml`, and local formats can be added under `config/reference_export_formats.d/`.

```bash
bookmem reference-formats
bookmem validate-reference-formats
bookmem export-references data/books --format bibtex --output exports/references.bib
```

See `docs/PLUGGABLE_REFERENCE_FORMATS.md` for the export format schema.


## MCP server

BookMem can expose the local corpus to MCP-capable agents:

```bash
bookmem serve-mcp
```

The server provides tools for search, reading chunks/sections/chapters,
query routing, book listing and topic mapping. See
`docs/MCP_SERVER.md` for configuration examples and tool details.


## Local HTTP API

BookMem can also run a small FastAPI service for local/container integrations:

```bash
bookmem serve
```

Default URL:

```text
http://127.0.0.1:8765
```

Key endpoints include `/books`, `/search`, `/route`, `/chunks/{chunk_id}`,
and `/books/{book_id}/chapters`. See `docs/LOCAL_API.md`.


## Obsidian notes

BookMem can generate human-facing Markdown notes for Obsidian:

```bash
bookmem notes generate "data/books/158.../Book.md" --write
bookmem notes generate "data/books/158.../Book.md" --type summary --write
bookmem notes generate "data/books/158.../Book.md" --type implementation-notes --write
```

Notes are written to `data/notes/` and include YAML frontmatter linking
them back to the canonical BookMem source. See `docs/OBSIDIAN_NOTES.md`.


## Clean check

Audit cleaned Markdown before indexing:

```bash
bookmem clean-check "data/books/158.../Book.md"
bookmem clean-check "data/books/158.../Book.md" --json
```

This reports remaining images, HTML, Pandoc spans, empty anchors, heading
quality, paragraph quality, ISBNs and frontmatter state. See
`docs/CLEAN_CHECK.md`.


## Cleaning profiles

Markdown cleanup is profile-driven:

```bash
bookmem cleaning-profiles
bookmem clean "Book.md" --profile epub_pandoc --output "Book.cleaned.md"
bookmem clean-books data/raw-books data/books --profile epub_pandoc
bookmem prepare-books data/raw-books --profile epub_pandoc --changed-only
```

Profiles live in `config/cleaning_profiles.yaml` and can be extended in
`config/cleaning_profiles.d/`. See `docs/CLEANING_PROFILES.md`.


## Testing

Install development dependencies and run the test suite:

```bash
pip install -e ".[dev]"
pytest
pytest tests/test_cleaning.py
```

The suite uses a small fixture corpus under `tests/fixtures/`. See
`docs/TESTING.md`.


## Doctor

Run a health check after upgrades or before exposing BookMem to agents:

```bash
bookmem doctor
bookmem doctor --fix
bookmem doctor --json
```

`--fix` only applies safe repairs such as creating missing folders,
`.gitkeep` placeholders or an empty manifest. See `docs/DOCTOR.md`.


## Docker

Build and run the API service:

```bash
docker compose build
docker compose up -d bookmem-api
```

Run one-off CLI commands:

```bash
docker compose run --rm bookmem-worker bookmem doctor
docker compose run --rm bookmem-worker bookmem ingest --changed-only
```

The compose file mounts `./data`, `./config` and `./exports` into the
container so the corpus remains on the host. See `docs/DOCKER.md`.


## API authentication

The local API can require a simple bearer token:

```bash
BOOKMEM_API_REQUIRE_KEY=true BOOKMEM_API_KEY=change-me bookmem serve
```

Or:

```bash
bookmem serve --require-api-key --api-key "change-me"
```

Use:

```http
Authorization: Bearer change-me
```

See `docs/API_AUTH.md`.


## Backup and restore

Create a portable backup of canonical and reviewable BookMem state:

```bash
bookmem backup --output backups/bookmem-2026-05-18.tar.gz
bookmem restore backups/bookmem-2026-05-18.tar.gz --dry-run
bookmem restore backups/bookmem-2026-05-18.tar.gz
```

Backups include `data/books`, `data/summaries`, `data/notes`,
`data/manifests`, `data/review`, `config` and project metadata. They
exclude `data/lancedb`, `.venv`, caches and exports. See
`docs/BACKUP_RESTORE.md`.


## Import adapters

Import source book formats into raw Markdown under `data/raw-books/`:

```bash
bookmem import epub "Book.epub"
bookmem import html "Book.html"
bookmem import pdf "Book.pdf"
bookmem import calibre "/path/to/Calibre Library"
```

The normal pipeline then takes over:

```text
import → raw Markdown → clean → frontmatter → classify → prepare → ingest
```

See `docs/IMPORT_ADAPTERS.md`.


## Calibre integration

Use Calibre as a metadata source without replacing BookMem frontmatter:

```bash
bookmem calibre scan "/path/to/Calibre Library"
bookmem calibre metadata "/path/to/Calibre Library" "Book Title"
bookmem calibre import "/path/to/Calibre Library"
bookmem calibre enrich "data/books/.../Book.md" "/path/to/Calibre Library" --write
```

See `docs/CALIBRE.md`.


## Grimmory integration

Export BookMem metadata as Grimmory-ready sidecar JSON files:

```bash
bookmem grimmory sidecar "data/books/.../Book.md"
bookmem grimmory export data/books --output-dir exports/grimmory
bookmem grimmory export data/books --output-dir exports/grimmory --copy-markdown
```

See `docs/GRIMMORY.md`.


## Metadata enrichment

Optional online metadata enrichment supports Library of Congress, Open
Library and Google Books:

```bash
bookmem enrich-openlibrary "data/books/.../Book.md" --write
bookmem enrich-google-books "data/books/.../Book.md" --write
bookmem enrich-metadata "data/books/.../Book.md" --providers loc,openlibrary,google --write
```

Enrichment fills missing metadata, records provenance in
`metadata_sources`, and does not overwrite reviewed fields unless
explicitly told to. See `docs/METADATA_ENRICHMENT.md`.


## Edition handling

Track works and editions separately so duplicate detection can tell the
difference between a true duplicate and a legitimate new edition:

```bash
bookmem editions
bookmem editions "The 7 Habits of Highly Effective People"
bookmem editions --write
```

Edition metadata uses `work:` and `edition:` frontmatter blocks. See
`docs/EDITIONS.md`.


## Book relationship graph

Build a derived graph of book-to-book relationships:

```bash
bookmem build-graph
bookmem related "Atomic Habits"
bookmem related --topic "systems thinking"
```

The graph is stored at `data/graphs/book_graph.json` and uses signals
such as shared topics, class, summaries, author and work/edition groups.
See `docs/BOOK_GRAPH.md`.


## Answer packs

Gather route, relevant books, passages, context, related books and
citations into one structured evidence bundle:

```bash
bookmem answer-pack "What do my books say about systems versus goals?"
bookmem answer-pack "What do my books say about systems versus goals?" --json
```

This is designed for Sandy and other agents that need evidence before
producing a final answer. See `docs/ANSWER_PACKS.md`.


## Summary providers

Deterministic summaries remain the default, with optional LLM-assisted
providers:

```bash
bookmem summary-providers
bookmem summarise-book "data/books/.../Book.md" --provider deterministic
bookmem summarise-book "data/books/.../Book.md" --provider openai
bookmem summarise-books data/books --provider local_ollama
```

LLM-assisted summaries are always marked as `review_status:
machine_draft` and record provider/model metadata. See
`docs/SUMMARY_PROVIDERS.md`.


## Prompt packs

Reusable prompt assets live under `prompts/`:

```bash
bookmem prompts list
bookmem prompts show summarise_book
bookmem prompts show answer_from_corpus
```

Included prompts cover summary generation, implementation notes,
classification, key model extraction and answering from corpus evidence.
See `docs/PROMPT_PACKS.md`.


## Concept extraction

Extract reusable concepts, models, frameworks and methods from books:

```bash
bookmem extract-concepts "data/books/.../Book.md"
bookmem concepts extract-books data/books
bookmem concepts search "circle of influence"
bookmem concepts list --class 158
```

Concepts are derived artefacts under `data/concepts/` and include source
chunks/citations. See `docs/CONCEPTS.md`.


## Index versioning

Check whether the retrieval index is stale compared with current
chunking, embedding, cleaning and taxonomy settings:

```bash
bookmem index-status
bookmem index-status --json
```

The manifest records index schema, chunker version, embedding model,
embedding dimension, cleaner version and taxonomy fingerprint. See
`docs/INDEX_VERSIONING.md`.


## Embedding model management

Manage embedding profiles, benchmark models and reindex safely:

```bash
bookmem embeddings info
bookmem embeddings models
bookmem embeddings benchmark --model bge-m3
bookmem embeddings reindex --model bge-m3
```

Embedding metadata is stored in the manifest and index fingerprint. See
`docs/EMBEDDINGS.md`.


## Retrieval evaluation

Measure retrieval quality with a small benchmark query set:

```bash
bookmem eval queries
bookmem eval retrieval
bookmem eval retrieval --json
```

Evaluation queries live in `eval/queries.yaml` and report Recall@K, MRR
and failed queries. See `docs/EVALUATION.md`.
