# Changelog

All notable changes to BookMem are documented in this file.

BookMem uses semantic versioning while it is under active early development. Until `1.0.0`, minor versions may still include CLI and schema changes, but each bump represents a coherent feature milestone.



## [0.16.0] - 2026-05-18

### Added

- Added topic map generation for agent reasoning.
- Added `bookmem/topic_maps.py`.
- Added `docs/TOPIC_MAPS.md`.
- Added `bookmem map-topic <query>` command.
- Topic maps combine:
  - deterministic routing,
  - book and chapter summary search,
  - indexed chunk retrieval,
  - recurring theme extraction,
  - evidence snippets with chunk citations where available.
- Added JSON/YAML output support for saved topic maps.

### Notes

- Topic maps are derived reasoning aids and can be regenerated. They do not replace canonical Markdown frontmatter or indexed chunk citations.

## [0.15.0] - 2026-05-18

### Added

- Added collection-level statistics reporting.
- Added `bookmem/stats.py`.
- Added `docs/STATS.md`.
- Added `bookmem stats` command.
- Added breakdowns by:
  - BMDC class
  - author
  - topic
- Added JSON output for dashboards and agent workflows.

### Notes

- Statistics are calculated from canonical Markdown frontmatter and manifest/index state.
- Chunk counts depend on the manifest and therefore reflect the last successful ingest.

## [0.14.0] - 2026-05-18

### Added

- Added duplicate and near-duplicate detection.
- Added `bookmem/duplicates.py`.
- Added `docs/DUPLICATES.md`.
- Added `bookmem duplicates` command with detection by:
  - ISBN
  - normalised title and author
  - normalised content hash
  - near-duplicate similarity
- Added optional duplicate review export to `data/review/possible_duplicates.yaml`.
- Added `bookmem review duplicates` to inspect duplicate review candidates.

### Notes

- Duplicate detection is deliberately non-destructive. BookMem flags candidates but does not delete, rename or move books automatically.

## [0.13.0] - 2026-05-18

### Added

- Added YAML-driven reference export format definitions.
- Added built-in reference export format file at `config/reference_export_formats.yaml`.
- Added local reference export format override directory at `config/reference_export_formats.d/`.
- Added commands:
  - `bookmem reference-formats`
  - `bookmem validate-reference-formats`
- Added `docs/PLUGGABLE_REFERENCE_FORMATS.md`.

### Changed

- `bookmem export-references` now loads BibTeX, RIS, CSL JSON and EndNote XML definitions from YAML rather than hard-coded Python branches.
- Existing built-in formats remain available: `bibtex`, `ris`, `csl-json`, `endnote-xml`.

### Notes

- Export formats are data-driven serialisation rules. The underlying canonical metadata remains the YAML frontmatter inside each cleaned Markdown book.

## [0.12.0] - 2026-05-18

### Added

- Added YAML-driven citation style definitions.
- Added built-in citation style file at `config/citation_styles.yaml`.
- Added local citation style override directory at `config/citation_styles.d/`.
- Added commands:
  - `bookmem citation-styles`
  - `bookmem validate-citation-styles`
- Added `docs/PLUGGABLE_CITATIONS.md`.

### Changed

- `bookmem cite` and `bookmem cite-books` now load styles from YAML rather than hard-coded Python branches.
- Existing built-in styles remain available: `apa`, `harvard`, `mla`, `chicago`.

### Notes

- Reference-manager exports became YAML-driven in `0.13.0`.


## [0.11.0] - 2026-05-18

### Added

- Added formatted book citation generation from canonical Markdown frontmatter.
- Added citation styles:
  - `apa`
  - `harvard`
  - `mla`
  - `chicago`
- Added reference manager exports:
  - `bibtex`
  - `ris`
  - `csl-json`
  - `endnote-xml`
- Added commands:
  - `bookmem cite <path> --style apa`
  - `bookmem cite-books <books_dir> --style harvard --output <file>`
  - `bookmem export-references <books_dir> --format bibtex --output <file>`
- Added `bookmem/citation_exports.py`.
- Added `docs/REFERENCE_EXPORTS.md`.

### Notes

- Reference exports use book-level frontmatter. Passage-level citations still come from indexed chunk metadata and line ranges.
- Formatted style output is intended as a practical working citation layer. Final university submissions should still be checked against the relevant institutional style guide.

## [0.10.0] - 2026-05-18

### Added

- Added generated review queue support under:

  ```text
  data/review/
    needs_metadata.yaml
    needs_classification.yaml
    low_confidence_matches.yaml
  ```

- Added review commands:
  - `bookmem review`
  - `bookmem review metadata`
  - `bookmem review classifications`
  - `bookmem review isbn-conflicts`
  - `bookmem review low-confidence`
  - `bookmem review apply`
- Added detection for missing title/author metadata.
- Added detection for multiple ISBNs in one book.
- Added duplicate detection by ISBN and by title/author pair.
- Added detection for external catalogue class conflicts.
- Added low-confidence classification review prompts.
- Added YAML-driven review application for approved metadata and classification edits.
- Added `bookmem/review.py`.
- Added `docs/REVIEW_QUEUE.md`.

### Changed

- Review application updates canonical Markdown frontmatter only. It does not silently delete, rename or move books.
- `.gitignore` now treats `data/review/` as generated operational state while preserving `.gitkeep`.

## [0.9.1] - 2026-05-18

### Changed

- Added explicit project authorship documentation.
- Added `AUTHORS.md` and `NOTICE`.
- Confirmed Martyn Forryan as the sole listed project author, creator and maintainer in package metadata and documentation.
- Cleaned release bundle attribution so Git author and committer metadata use Martyn Forryan.

## [0.9.0] - 2026-05-18

### Added

- Added citation and quote support throughout indexed chunks.
- Added line range metadata during chunking:
  - `start_line`
  - `end_line`
  - `heading_path`
  - `chapter_id`
  - `chapter_title`
  - `section_id`
  - `section_title`
- Added a reusable `citation` field to each chunk.
- Updated search and reading commands to display source path, heading context and line ranges.
- Added `docs/CITATIONS.md`.

### Changed

- LanceDB schema now includes citation metadata. Existing indexes should be rebuilt with:

  ```bash
  bookmem ingest --reset
  ```

## [0.8.0] - 2026-05-18

### Added

- Added richer agent reading/navigation tools:
  - `bookmem read-around <chunk_id> --before 2 --after 3`
  - `bookmem read-section --chunk-id <chunk_id>`
  - `bookmem read-chapter --book <book_id> --chapter "Chapter 6"`
- Added chunk neighbour metadata:
  - `previous_chunk_id`
  - `next_chunk_id`
- Added chapter and section metadata:
  - `chapter_id`
  - `chapter_title`
  - `section_id`
  - `section_title`
- Added `docs/READING_TOOLS.md`.

### Changed

- Chunking now preserves enough structure for agents to expand context safely without reading an entire book by default.

## [0.7.0] - 2026-05-18

### Added

- Added deterministic query routing with `bookmem route`.
- Added routed retrieval with `bookmem ask-search`.
- Added optional summary-first search behaviour.
- Added routed fallback handling for low/no-result searches.
- Added `bookmem/router.py`.
- Added `docs/ROUTER.md`.

### Notes

- The router is rules-based. It uses configured BMDC aliases, class labels, topic hints and matched query terms. It does not call an LLM.

## [0.6.0] - 2026-05-18

### Added

- Added book-level and chapter-level summary maps.
- Added derived summary files under:

  ```text
  data/summaries/<book_id>/book.yaml
  data/summaries/<book_id>/chapters.yaml
  ```

- Added commands:
  - `bookmem summarise-book <path>`
  - `bookmem summarise-books <path>`
  - `bookmem search-summaries <query>`
- Added `bookmem/summaries.py`.
- Added `docs/SUMMARIES.md`.
- Manifest records now include summary state where available.

### Notes

- The first summary generator is deterministic and offline. It produces draft maps from frontmatter, headings, early chapter text, routing aliases and extracted keywords.

## [0.5.0] - 2026-05-18

### Added

- Added manifest support and changed-file detection.
- Added generated manifest at:

  ```text
  data/manifests/books.json
  ```

- Manifest records track:
  - `book_id`
  - `source_path`
  - `canonical_path`
  - `content_hash`
  - `frontmatter_hash`
  - `full_hash`
  - `source_content_hash`
  - `last_prepared`
  - `last_indexed`
  - `chunk_count`
  - `classification_source`
  - `cleaner_version`
- Added commands:
  - `bookmem status`
  - `bookmem ingest --changed-only`
  - `bookmem prepare-book <path> --changed-only`
  - `bookmem prepare-books <path> --changed-only`
- Added `bookmem/manifest.py`.
- Added `docs/MANIFEST.md`.

## [0.4.0] - 2026-05-18

### Added

- Added automatic prepare, rename and placement workflow.
- Added `bookmem prepare-book` and `bookmem prepare-books`.
- Added canonical file naming from inferred metadata:

  ```text
  <Title> - <Author> - <ISBN>.md
  ```

- Added automatic placement into BMDC class folders.
- Added conservative overwrite flags for canonical files and frontmatter.
- Added `bookmem/prepare.py`.
- Added `docs/PREPARE_BOOKS.md`.

### Changed

- Classification now weights title/headings more heavily than incidental body mentions.

## [0.3.0] - 2026-05-18

### Added

- Added Markdown cleanup tooling for noisy EPUB/Pandoc-style exports.
- Added commands:
  - `bookmem clean <path>`
  - `bookmem clean <path> --in-place`
  - `bookmem clean-books <source_dir> <destination_dir>`
- Added canonical frontmatter workflow.
- Added commands:
  - `bookmem frontmatter show <path>`
  - `bookmem frontmatter generate <path>`
  - `bookmem frontmatter generate-books <path>`
  - `bookmem frontmatter validate <path>`
- Added filename metadata inference for files named:

  ```text
  <Title> - <Author> - <ISBN>.md
  ```

- Added ISBN discovery from Markdown body text with check-digit validation.
- Added optional Library of Congress ISBN enrichment through SRU/MARCXML.
- Added commands:
  - `bookmem scan-isbns <path>`
  - `bookmem loc-lookup <isbn>`
  - `bookmem enrich-loc <path>`
  - `bookmem enrich-loc-books <path>`
- Added documentation:
  - `docs/BOOK_CLEANUP.md`
  - `docs/FRONTMATTER.md`
  - `docs/FILENAME_METADATA.md`
  - `docs/ISBN_DISCOVERY.md`
  - `docs/LOC_ENRICHMENT.md`

### Notes

- Library of Congress enrichment is optional and online. The core prepare/ingest workflow remains usable offline.

## [0.2.0] - 2026-05-18

### Added

- Added GPL-3.0-only licensing.
- Added `LICENSE`.
- Added BookMem Decimal Classification (BMDC) taxonomy.
- Added `config/bmdc.yaml`.
- Added taxonomy documentation:
  - `docs/TAXONOMY.md`
  - `docs/CLASSIFICATION_IP.md`
- Added BMDC-compatible terminology:
  - `class_code`
  - `primary_class`
  - `secondary_classes`
  - routing aliases

### Changed

- Renamed the internal classification scheme from the early working name to **BookMem Decimal Classification (BMDC)**.
- Clarified that BMDC uses compatible numeric class identifiers with original BookMem wording, labels, aliases and documentation.

## [0.1.0] - 2026-05-18

### Added

- Initial BookMem starter project.
- Added Python package and CLI entry point.
- Added LanceDB-backed Markdown book indexing.
- Added local embedding support via Sentence Transformers.
- Added hybrid/vector/full-text search modes where supported by the installed LanceDB version.
- Added basic commands:
  - `bookmem ingest`
  - `bookmem search`
  - `bookmem read`
  - `bookmem list-books`
- Added initial project layout:

  ```text
  data/books/
  data/lancedb/
  data/manifests/
  config/
  docs/
  ```

