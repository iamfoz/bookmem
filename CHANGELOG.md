# Changelog

All notable changes to BookMem will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

BookMem is pre-1.0 software. Minor releases may include CLI, config or schema changes while
the project is stabilising.

## [Unreleased]

### Added
- Reserved for changes not yet released.


## [0.63.1] - 2026-05-22

### Fixed
- Book discovery no longer skips a corpus stored under a hidden directory.
  Exclusion rules are now evaluated against each file's path relative to the
  corpus root, so the Hermes runtime home (`~/.hermes/bookmem`, under the
  hidden `~/.hermes` directory) is scanned correctly. Previously `ingest`,
  `summarise-books` and other commands reported "No Markdown files found" on
  a Hermes install because the leading `.hermes` path component was treated
  as a hidden directory to skip.


## [0.63.0] - 2026-05-22

### Added
- First-class Hermes agent integration. BookMem now resolves a runtime root
  (`BOOKMEM_HOME`) that is independent of the repository checkout and of the
  Hermes virtualenv.
- `bookmem/paths.py`, a central path resolver. The runtime root is resolved in
  order from: the `--home` option, the `BOOKMEM_HOME` environment variable, the
  active profile's `paths.home_dir`, Hermes auto-detection, and finally the
  current working directory (standalone fallback).
- Global `bookmem --home PATH` option to set the runtime root for a command.
- `bookmem hermes init` to create the `~/.hermes/bookmem` runtime home and seed
  it with default config. Idempotent; supports `--dry-run` and `--force`.
- `bookmem hermes status`, a passive Hermes health check that does not load
  embedding models, initialise LanceDB or contact Hugging Face.
- `bookmem hermes install-wrapper` to create `~/.hermes/bin/bookmem`, a wrapper
  that sets `BOOKMEM_HOME` and runs BookMem from the Hermes venv with the
  `hermes` profile. `bookmem hermes install-help` prints the install commands.
- A `hermes` config profile and `contrib/hermes/` integration assets: an
  install script, a Hermes tool manifest, an agent skill guide and a README.
- The default `config/` tree is packaged into the wheel so `bookmem hermes
  init` can seed config without the repository checkout on disk.

### Changed
- Config profiles now drive runtime path resolution consistently: a profile's
  `paths.home_dir` seeds `BOOKMEM_HOME`, and `config.get_settings()` derives
  its directory defaults from the central path resolver.

### Fixed
- BookMem runtime data is no longer tied to the current working directory.
  Hermes installs keep data and config under `~/.hermes/bookmem`, never inside
  the Hermes virtualenv, and do not require the repository checkout to be the
  working directory.
- Machine-readable `--json` CLI output is emitted without Rich line-wrapping,
  so piped JSON is no longer corrupted at the console width.


## [0.62.1] - 2026-05-22

### Fixed
- Fixed broken imports that prevented several modules from loading: `topic_maps`
  imports in `web_ui.py`, `reading_lists.py` and `saved_queries.py`, the `map_topic`
  import and call signature in `api.py` and `mcp_server.py`, `summary_paths` in
  `notes.py`, and a missing `import tempfile` in `restore_points.py`.
- Fixed a Python 3.11 f-string `SyntaxError` that made `web_ui.py` unimportable.
- Restored the `BookMemTUI` class indentation so `bookmem tui` starts, and declared
  the `textual` dependency it requires.
- Fixed `summarise-books`, `answer-pack --json`, recurring brief generation and
  `passages favourite`, which crashed on valid inputs.
- Fixed topic comparison and reading-list generation silently dropping summary and
  graph matches.
- Guarded section chunking against an infinite loop when chunk overlap met or
  exceeded the target size.
- Fixed Calibre author/tag parsing and removed literal newline escapes from
  generated Calibre stubs and `bookmem migrations create` scaffolding.
- Corrected the recall@k retrieval metric, edition ordinal labels, book-ID
  generation with null authors, and `bookmem stats` skipping the difficulty,
  density and best-read-as tables when no topics were present.
- Removed redundant per-pair summary file reads when building the book graph.
- Updated the test suite to current function signatures and removed unused
  imports and variables.

### Security
- Hardened backup and restore-point archive extraction against path traversal.
- Used a constant-time comparison for the API bearer token.


## [0.62.0] - 2026-05-22

### Added
- Added full documentation suite with installation, quick start, Hermes integration,
  command reference, architecture, operations and troubleshooting.
- Added Standard README-style root README with practical usage examples.

### Changed
- Reworked changelog to follow Keep a Changelog 1.1.0.
- Updated project URLs to `https://github.com/iamfoz/bookmem`.

## [0.61.10] - 2026-05-20

### Fixed
- Removed incorrect project URLs from `pyproject.toml`.
- Added shared book Markdown discovery helpers in `bookmem/book_files.py`.
- Excluded support Markdown files such as `README.md`, `CHANGELOG.md`, `LICENSE.md`,
  `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` and `SECURITY.md` from book discovery.
- Applied the book-file filter to ingestion, summary generation, frontmatter discovery,
  review queues, citations, duplicate detection, statistics, agent exports and CLI bulk
  Markdown scans.
- Prevented sample-directory README files from being prepared, summarised, indexed or
  exported as books.
- Fixed deterministic summary generation when Markdown section splitting returns richer
  tuples such as `(level, heading, text)`.
- Made `bookmem setup status` passive by default so it does not load embedding models,
  initialise LanceDB or contact Hugging Face unless explicitly requested.
- Added `bookmem setup status --include-index` for explicit embedding/LanceDB diagnostics.
- Fixed setup and doctor compatibility issues introduced during CLI refactoring.
- Fixed concept command option naming so `bookmem --help` no longer fails with duplicate
  Click parameter declarations.
- Restored backwards-compatible frontmatter helper wrappers used by older modules.

### Changed
- CLI command imports are lazy, keeping lightweight commands such as `bookmem --help`,
  `bookmem profile`, `bookmem plugins` and `bookmem setup presets` fast.
- Setup diagnostics separate passive status checks from heavier index diagnostics.

## [0.61.0] - 2026-05-19

### Added
- Added `bookmem doctor --deep` for read-only integrity diagnostics.
- Added sampled checks for readable chunks and valid citation line ranges.
- Added manifest path checks, summary/book ID checks, concept source chunk checks and
  graph node integrity checks.
- Added embedding dimension consistency checks against manifest/index metadata.
- Added review queue and config parsing checks.

### Changed
- Doctor JSON output includes a `deep` section when deep diagnostics are requested.
- Overall doctor status reflects deep diagnostic warnings or failures when `--deep` is used.

## [0.60.0] - 2026-05-18

### Added
- Added jobs and observability ledger under `data/jobs/`.
- Added `bookmem jobs list`, `bookmem jobs status <job_id>` and `bookmem jobs tail <job_id>`.
- Added `JobTracker` helper APIs for future long-running workflows.
- Job records track started/finished timestamps, status, command, progress, current file,
  processed file count, warnings, errors and message.

## [0.59.0] - 2026-05-17

### Added
- Added config profiles/environments under `config/profiles/`.
- Added built-in `local`, `docker` and `assistant_agent` profiles.
- Added global `bookmem --profile <name>` support.
- Added `bookmem profile current`, `profile list`, `profile show`, `profile use` and
  `profile validate`.

### Changed
- Profiles can set data/config/export/backup/index paths, API/MCP defaults, retrieval
  defaults, permissions profile and feature flags.
- `BOOKMEM_PROFILE` takes precedence over the persisted profile file.

## [0.58.0] - 2026-05-16

### Added
- Added lightweight YAML-manifest plugin discovery.
- Added plugin directories for importers, enrichers, exporters, summary providers and citation
  styles.
- Added `bookmem plugins list` and `bookmem plugins validate`.
- Added example plugin manifests.

### Changed
- Plugin entrypoint metadata is validated but not executed.

## [0.57.0] - 2026-05-15

### Added
- Added book graph visualisation exports.
- Added `bookmem graph export --format graphml`, `cytoscape`, `mermaid`, `obsidian-canvas`
  and `all`.
- Added `bookmem graph formats`.
- Added GraphML, Cytoscape JSON, Mermaid and Obsidian Canvas output under `exports/graphs/`.

## [0.56.0] - 2026-05-14

### Added
- Added claims extraction as a separate research layer from concepts.
- Added `bookmem extract-claims`, `bookmem claims search` and `bookmem claims compare`.
- Added claim records with claim text, stance, confidence, source chunks, citation, tags and
  review status.
- Added Markdown and JSON output for claim comparisons.

## [0.55.0] - 2026-05-13

### Added
- Added topic disagreement/contradiction mapping.
- Added `bookmem compare-topic`.
- Added stance grouping for favouring, criticising, mixed/context-dependent and neutral evidence.
- Added generated topic tensions and Markdown/JSON output.

## [0.54.0] - 2026-05-12

### Added
- Added quote/passages/commonplace-book support.
- Added `bookmem passages extract`, `passages search`, `passages favourite` and `passages export`.
- Added `data/passages/extracted.yaml` and `data/passages/favourites.yaml`.
- Added Obsidian Markdown, JSONL and YAML passage export formats.

## [0.53.0] - 2026-05-11

### Added
- Added reading metadata inference.
- Added `bookmem reading-metadata infer`.
- Added `bookmem stats --by-difficulty`.
- Added reading metadata fields for difficulty, estimated pages, estimated reading hours,
  density and best-read-as.
- Added reading metadata integration into reading-list generation.

## [0.52.0] - 2026-05-10

### Added
- Added ordered reading-list generation.
- Added `bookmem reading-list`, including `--topic`, `--goal`, `--limit`, `--save` and JSON
  output.
- Added saved reading-list outputs under `data/reading-lists/`.

### Changed
- Reading-list generation combines routing, passage search, summaries, concepts, topic maps
  and graph relationships.

## [0.51.0] - 2026-05-09

### Added
- Added saved queries and recurring research briefs.
- Added `bookmem query save`, `query list`, `query run` and `brief generate`.
- Added `data/queries/` and `data/briefs/`.
- Added example saved queries for systems thinking and personal finance.

## [0.50.0] - 2026-05-08

### Added
- Added workspace/project views for scoped retrieval.
- Added `config/workspaces.yaml`.
- Added `bookmem workspace list`, `workspace validate`, `workspace search` and
  `workspace answer-pack`.
- Added built-in productivity, finance and agent infrastructure workspaces.

## [0.49.0] - 2026-05-07

### Added
- Added agent permissions and safety policy support.
- Added `config/agent_permissions.yaml`.
- Added `bookmem permissions check` and `permissions list`.
- Added restore points and audit-linked rollback support.

### Changed
- Default agent examples use a generic `assistant_agent` profile rather than a named personal
  assistant.

## [0.48.0] - 2026-05-06

### Added
- Added durable audit logging under `data/audit/bookmem.log.jsonl`.
- Added `bookmem audit tail`, `audit search` and `audit export`.
- Added human review workflow for machine-generated summaries and concepts.
- Added generated artefact cleanup commands for summaries, concepts, graphs, index data and
  other derived state.

## [0.47.0] - 2026-05-05

### Added
- Added migration system with `bookmem migrations status`, `apply` and `create`.
- Added migration tracking under `data/manifests/migrations.json`.
- Added first-run setup wizard presets and setup status commands.
- Added richer TUI-oriented progress/status output for long-running setup steps.

## [0.46.0] - 2026-05-04

### Added
- Added Web UI entrypoint with `bookmem ui`.
- Added dashboard views for books, classes, review queues, duplicates, search, topic maps,
  clean-check reports, status and controls.
- Added retrieval evaluation set support with `bookmem eval retrieval`.

## [0.45.0] - 2026-05-03

### Added
- Added embedding model management.
- Added `bookmem embeddings info`, `models`, `benchmark` and `reindex`.
- Added index/model versioning with stale index detection.
- Added manifest metadata for chunker version, cleaner version, embedding model, embedding
  dimension and taxonomy version.

## [0.44.0] - 2026-05-02

### Added
- Added concept extraction.
- Added `bookmem extract-concepts`, `concepts search` and `concepts list`.
- Added prompt packs under `prompts/` with `bookmem prompts list` and `prompts show`.
- Added optional LLM-assisted summary providers.

## [0.43.0] - 2026-05-01

### Added
- Added answer-pack generation for structured evidence bundles.
- Added book relationship graph generation.
- Added edition/work handling for distinguishing duplicates from legitimate editions.
- Added Open Library and Google Books metadata enrichment fallbacks.

## [0.42.0] - 2026-04-30

### Added
- Added Calibre integration and import adapters.
- Added `bookmem calibre scan`, `calibre import` and `calibre metadata`.
- Added EPUB, PDF, HTML and Calibre import commands that normalise input to raw Markdown.
- Added Grimmory sidecar/export support.

## [0.41.0] - 2026-04-29

### Added
- Added backup and restore commands.
- Added optional API bearer-token authentication for the local FastAPI service.
- Added Docker support with Dockerfile, Compose file and Docker documentation.

## [0.40.0] - 2026-04-28

### Added
- Added local FastAPI service with `bookmem serve`.
- Added MCP server tooling for direct agent integration.
- Added agent export formats for JSONL, LlamaIndex, LangChain and Markdown indexes.
- Added Obsidian-friendly book notes.

## [0.30.0] - 2026-04-24

### Added
- Added quality checks for cleaned Markdown.
- Added configurable cleaning profiles.
- Added test suite and fixture corpus.
- Added `bookmem doctor` for broad health checks and optional conservative fixes.

## [0.20.0] - 2026-04-20

### Added
- Added manifest and changed-file detection.
- Added book-level and chapter-level summaries.
- Added deterministic query router.
- Added read-around, read-chapter and read-section tools.
- Added quote/citation support with line ranges and heading paths.
- Added review queues, duplicate detection, collection statistics, topic maps and export formats.

## [0.10.0] - 2026-04-15

### Added
- Added initial BookMem CLI and project structure.
- Added GPL-3.0-only project metadata.
- Added BMDC-oriented classification support using original wording and descriptions.
- Added Markdown cleaning, frontmatter generation, Library of Congress lookup and canonical
  file preparation.
- Added LanceDB ingestion and basic hybrid retrieval commands.

[Unreleased]: https://github.com/iamfoz/bookmem/compare/v0.63.1...HEAD
[0.63.1]: https://github.com/iamfoz/bookmem/compare/v0.63.0...v0.63.1
[0.63.0]: https://github.com/iamfoz/bookmem/compare/v0.62.1...v0.63.0
[0.62.1]: https://github.com/iamfoz/bookmem/compare/v0.62.0...v0.62.1
[0.62.0]: https://github.com/iamfoz/bookmem/compare/v0.61.10...v0.62.0
[0.61.10]: https://github.com/iamfoz/bookmem/compare/v0.61.0...v0.61.10
[0.61.0]: https://github.com/iamfoz/bookmem/compare/v0.60.0...v0.61.0
[0.60.0]: https://github.com/iamfoz/bookmem/compare/v0.59.0...v0.60.0
[0.59.0]: https://github.com/iamfoz/bookmem/compare/v0.58.0...v0.59.0
[0.58.0]: https://github.com/iamfoz/bookmem/compare/v0.57.0...v0.58.0
[0.57.0]: https://github.com/iamfoz/bookmem/compare/v0.56.0...v0.57.0
[0.56.0]: https://github.com/iamfoz/bookmem/compare/v0.55.0...v0.56.0
[0.55.0]: https://github.com/iamfoz/bookmem/compare/v0.54.0...v0.55.0
[0.54.0]: https://github.com/iamfoz/bookmem/compare/v0.53.0...v0.54.0
[0.53.0]: https://github.com/iamfoz/bookmem/compare/v0.52.0...v0.53.0
[0.52.0]: https://github.com/iamfoz/bookmem/compare/v0.51.0...v0.52.0
[0.51.0]: https://github.com/iamfoz/bookmem/compare/v0.50.0...v0.51.0
[0.50.0]: https://github.com/iamfoz/bookmem/compare/v0.49.0...v0.50.0
[0.49.0]: https://github.com/iamfoz/bookmem/compare/v0.48.0...v0.49.0
[0.48.0]: https://github.com/iamfoz/bookmem/compare/v0.47.0...v0.48.0
[0.47.0]: https://github.com/iamfoz/bookmem/compare/v0.46.0...v0.47.0
[0.46.0]: https://github.com/iamfoz/bookmem/compare/v0.45.0...v0.46.0
[0.45.0]: https://github.com/iamfoz/bookmem/compare/v0.44.0...v0.45.0
[0.44.0]: https://github.com/iamfoz/bookmem/compare/v0.43.0...v0.44.0
[0.43.0]: https://github.com/iamfoz/bookmem/compare/v0.42.0...v0.43.0
[0.42.0]: https://github.com/iamfoz/bookmem/compare/v0.41.0...v0.42.0
[0.41.0]: https://github.com/iamfoz/bookmem/compare/v0.40.0...v0.41.0
[0.40.0]: https://github.com/iamfoz/bookmem/compare/v0.30.0...v0.40.0
[0.30.0]: https://github.com/iamfoz/bookmem/compare/v0.20.0...v0.30.0
[0.20.0]: https://github.com/iamfoz/bookmem/compare/v0.10.0...v0.20.0
[0.10.0]: https://github.com/iamfoz/bookmem/releases/tag/v0.10.0
