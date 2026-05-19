# Changelog

All notable changes to BookMem are documented in this file.

BookMem uses semantic versioning while it is under active early development. Until `1.0.0`, minor versions may still include CLI and schema changes, but each bump represents a coherent feature milestone.

























































## [0.61.10] - 2026-05-18

### Fixed
- Removed incorrect project URLs from `pyproject.toml`.
- Added shared book Markdown discovery helpers in `bookmem/book_files.py`.
- Excluded support files such as `README.md`, `CHANGELOG.md`, `LICENSE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `SECURITY.md` from book discovery.
- Applied the book-file filter to ingestion, summaries, summary providers, frontmatter discovery, review, citations, duplicates, stats, agent exports and CLI bulk file scans.
- Prevented README files in sample/data directories from being treated as books.

## [0.61.9] - 2026-05-18

### Fixed
- Fixed deterministic summary generation when `split_by_markdown_headings()` returns richer section tuples such as `(level, heading, text)`.
- Added section normalisation in `summary_providers.py` so summary providers accept tuple/list/dict section shapes.

## [0.61.8] - 2026-05-18

### Fixed
- Made `bookmem setup status` passive by default.
- `bookmem setup status` no longer loads embedding models, initialises LanceDB, or downloads from Hugging Face.
- Added `bookmem setup status --include-index` for explicit embedding/LanceDB diagnostics.

## [0.61.7] - 2026-05-18

### Fixed
- Fixed `doctor.collection_counts()` to use actual review queue keys: `metadata`, `classification`, and `low_confidence`.
- Kept `possible_duplicates.yaml` counting as an optional direct review file.
- Fixed `bookmem setup status` so missing LanceDB/index dependencies report a warning instead of crashing.

## [0.61.6] - 2026-05-18

### Fixed
- Fixed `bookmem setup status` / `bookmem doctor` review queue counting.
- `doctor.collection_counts()` now passes logical queue names to `review_file_path()` instead of YAML filenames.

## [0.61.5] - 2026-05-18

### Fixed
- Fixed `bookmem setup presets` importing `index_versions`/LanceDB at module import time.
- Setup preset listing now only loads setup preset configuration; heavier index checks remain lazy inside setup status/preflight operations.

## [0.61.4] - 2026-05-18

### Fixed
- Restored backwards-compatible `frontmatter.discover_book_files` helper.
- Restored backwards-compatible `frontmatter.read_frontmatter_and_body` helper.
- Fixed setup/doctor imports that still expected those helpers after the frontmatter refactor.

## [0.61.3] - 2026-05-18

### Fixed
- Fixed Typer/Click parameter declaration collision in concept commands.
- `bookmem --help` no longer fails with `TypeError: Name 'class_code' defined twice`.

## [0.61.2] - 2026-05-18

### Fixed
- Fixed missing `jobs_app` and `profile_app` Typer declarations after the lazy CLI import refactor.
- Added a CLI wiring sanity check during patching to catch command groups used before declaration.

## [0.61.1] - 2026-05-18

### Fixed
- Fixed slow/hanging CLI startup caused by importing embedding/index modules at import time.
- `bookmem --help` no longer imports `sentence-transformers`, `sklearn` or `scipy`.
- Replaced eager CLI imports with lazy command-level wrappers.

## [0.61.0] - 2026-05-18

### Added
- Added `bookmem doctor --deep`.
- Added `bookmem doctor --deep --sample-size`.
- Added `bookmem/doctor_deep.py`.
- Added deep diagnostics for sampled chunks, citation line ranges, manifest paths, summaries, concept source chunks, graph nodes, embedding dimensions, review queues and config parsing.

### Behaviour
- Deep doctor mode is read-only and does not run migrations.
- Deep doctor results are included under `deep` in JSON output.
- Overall doctor status now reflects deep diagnostic warnings/failures when `--deep` is used.

## [0.60.0] - 2026-05-18

### Added
- Added jobs and observability ledger.
- Added `data/jobs/`.
- Added `bookmem jobs list`.
- Added `bookmem jobs status <job_id>`.
- Added `bookmem jobs tail <job_id>`.
- Added `bookmem/jobs.py`.
- Added `docs/JOBS.md`.
- Added `JobTracker` helper for future long-running workflows.

### Behaviour
- Job status files track started/finished timestamps, status, command, progress, current file, files processed, errors, warnings and message.
- Job logs are written as line-oriented text under `data/jobs/<job_id>.log`.

## [0.59.0] - 2026-05-18

### Added
- Added config profiles/environments.
- Added global `bookmem --profile <name>` option.
- Added `config/profiles/local.yaml`.
- Added `config/profiles/docker.yaml`.
- Added `config/profiles/assistant_agent.yaml`.
- Added `bookmem profile current`.
- Added `bookmem profile list`.
- Added `bookmem profile show`.
- Added `bookmem profile use`.
- Added `bookmem profile validate`.
- Added `bookmem/profiles.py`.
- Added `docs/PROFILES.md`.

### Behaviour
- Profiles can set data/config/export/backup/index paths, API/MCP defaults, retrieval defaults, permissions profile and feature flags.
- `BOOKMEM_PROFILE` is supported and takes precedence over the persisted current profile.
- `bookmem profile use` persists the selected profile in `data/manifests/current_profile.yaml`.
- The built-in agent profile is generic: `assistant_agent`.

## [0.58.0] - 2026-05-18

### Added
- Added lightweight plugin architecture.
- Added `plugins/`.
- Added plugin category directories:
  - `plugins/importers/`
  - `plugins/enrichers/`
  - `plugins/exporters/`
  - `plugins/summary_providers/`
  - `plugins/citation_styles/`
- Added example plugin manifests.
- Added `bookmem plugins list`.
- Added `bookmem plugins validate`.
- Added `bookmem/plugins.py`.
- Added `docs/PLUGINS.md`.

### Behaviour
- Plugin discovery is YAML-manifest based.
- Optional entrypoint metadata is validated but not executed.
- Validation checks categories, duplicate IDs, capabilities and importable entrypoint modules.

## [0.57.0] - 2026-05-18

### Added
- Added graph visualisation exports.
- Added `bookmem graph export --format graphml`.
- Added `bookmem graph export --format cytoscape`.
- Added `bookmem graph export --format mermaid`.
- Added `bookmem graph export --format obsidian-canvas`.
- Added `bookmem graph export --format all`.
- Added `bookmem graph formats`.
- Added `bookmem/graph_exports.py`.
- Added `docs/GRAPH_EXPORTS.md`.

### Behaviour
- GraphML exports to `exports/graphs/book_graph.graphml`.
- Cytoscape JSON exports to `exports/graphs/book_graph.cyjs`.
- Mermaid exports to `exports/graphs/book_graph.mmd`.
- Obsidian Canvas exports to `exports/graphs/book_graph.canvas`.
- Graph export writes audit records.

## [0.56.0] - 2026-05-18

### Added
- Added claims extraction.
- Added `bookmem extract-claims`.
- Added `bookmem claims search`.
- Added `bookmem claims compare`.
- Added `bookmem claims compare --markdown`.
- Added `bookmem/claims.py`.
- Added `data/claims/`.
- Added `docs/CLAIMS.md`.

### Behaviour
- Claims are stored in `data/claims/claims.yaml`.
- Claims include claim text, stance, confidence, source chunks, citation, tags and review status.
- Claim comparison groups claims into supports, challenges, qualifies and neutral.
- Claims are marked `review_status: machine_draft`.
- Claim extraction and comparison write audit records.

## [0.55.0] - 2026-05-18

### Added
- Added contradiction/disagreement mapping.
- Added `bookmem compare-topic`.
- Added `bookmem compare-topic --json`.
- Added `bookmem compare-topic --markdown`.
- Added `bookmem/topic_compare.py`.
- Added `docs/TOPIC_COMPARISON.md`.

### Behaviour
- Topic comparison groups evidence into favouring, criticising, mixed and neutral stances.
- Comparison uses curated passages, summaries and chunk search.
- Generated comparisons include tensions and are marked `review_status: machine_draft`.
- Topic comparison writes audit records.

## [0.54.0] - 2026-05-18

### Added
- Added quote/passages/commonplace-book layer.
- Added `bookmem passages extract`.
- Added `bookmem passages search`.
- Added `bookmem passages favourite`.
- Added `bookmem passages export`.
- Added `bookmem/passages.py`.
- Added `data/passages/`.
- Added `docs/PASSAGES.md`.

### Behaviour
- Extracted passages are written to `data/passages/extracted.yaml`.
- Favourited passages are written to `data/passages/favourites.yaml`.
- Passage records include quote, summary, why-it-matters, source chunk, citation, tags and review status.
- Passage export supports Obsidian Markdown, JSONL and YAML.
- Passage operations write audit records.

## [0.53.0] - 2026-05-18

### Added
- Added reading metadata inference.
- Added `bookmem reading-metadata infer`.
- Added `bookmem stats --by-difficulty`.
- Added `bookmem/reading_metadata.py`.
- Added `docs/READING_METADATA.md`.
- Added reading metadata fields: difficulty, estimated pages, estimated reading hours, density and best-read-as.
- Added reading metadata integration into reading-list generation.
- Added reading difficulty/density/best-read-as collection statistics.

### Behaviour
- Inferred reading metadata is marked `review_status: machine_draft`.
- Existing human-reviewed reading metadata is not overwritten by default.
- Writing inferred reading metadata records an audit entry.

## [0.52.0] - 2026-05-18

### Added
- Added reading-list generation.
- Added `bookmem reading-list`.
- Added `bookmem reading-list --topic`.
- Added `bookmem reading-list --goal`.
- Added `bookmem reading-list --save`.
- Added `bookmem/reading_lists.py`.
- Added `data/reading-lists/`.
- Added `docs/READING_LISTS.md`.

### Behaviour
- Reading lists combine routing, passage search, summaries, concepts, topic maps and graph relationships.
- Reading-list items include why the book is recommended, evidence and suggested reading posture.
- Saved reading lists are written as JSON and Markdown.
- Reading-list generation writes audit records.

## [0.51.0] - 2026-05-18

### Added
- Added saved queries.
- Added recurring research briefs.
- Added `data/queries/`.
- Added `data/briefs/`.
- Added example saved queries `systems-thinking.yaml` and `personal-finance.yaml`.
- Added `bookmem query save`.
- Added `bookmem query list`.
- Added `bookmem query run`.
- Added `bookmem brief generate`.
- Added `bookmem/saved_queries.py`.
- Added `docs/SAVED_QUERIES_AND_BRIEFS.md`.

### Behaviour
- Saved queries can optionally target a workspace.
- Briefs include best books, top passages, related concepts, topic maps, changed books/summaries since last run, suggested synthesis and citations.
- Briefs are written as JSON and Markdown by default.
- Saving queries and generating briefs write audit records.

## [0.50.0] - 2026-05-18

### Added
- Added workspace/project views for scoped retrieval.
- Added `config/workspaces.yaml`.
- Added `bookmem workspace list`.
- Added `bookmem workspace validate`.
- Added `bookmem workspace search <workspace> <query>`.
- Added `bookmem workspace answer-pack <workspace> <query>`.
- Added `bookmem/workspaces.py`.
- Added `docs/WORKSPACES.md`.
- Added built-in workspaces for productivity, finance and agent infrastructure.

### Behaviour
- Workspace search scopes retrieval using classes, routing aliases and topics.
- Workspace answer packs include workspace metadata and scoped results so agents can prefer project-specific evidence.

## [0.49.1] - 2026-05-18

### Changed
- Replaced the default Sandy-specific permissions profile name with generic `assistant_agent`.
- Updated docs and examples to refer to generic agents rather than a specific named assistant.
- Kept agent permissions fully customisable through `config/agent_permissions.yaml`.

## [0.49.0] - 2026-05-18

### Added
- Added agent permissions and safety policy.
- Added `config/agent_permissions.yaml`.
- Added `bookmem permissions check`.
- Added `bookmem permissions list`.
- Added `bookmem permissions agents`.
- Added `bookmem permissions validate`.
- Added `bookmem/permissions.py`.
- Added `docs/AGENT_PERMISSIONS.md`.
- Added built-in profiles for `sandy`, `readonly` and `admin`.

### Behaviour
- Permission decisions are `allow`, `require_confirmation`, `deny` or `unknown`.
- Deny rules take precedence over confirmation and allow rules.
- Unknown actions should be treated as unsafe until explicitly configured.
- `bookmem permissions check` uses script-friendly exit codes: 0 allowed, 2 denied/unknown, 3 confirmation required.

## [0.48.0] - 2026-05-18

### Added
- Added restore points and rollback.
- Added `bookmem restore-points create`.
- Added `bookmem restore-points list`.
- Added `bookmem restore-points show`.
- Added `bookmem rollback`.
- Added `bookmem rollback --last`.
- Added `bookmem rollback --audit-id`.
- Added `bookmem/restore_points.py`.
- Added `data/restore-points/`.
- Added `docs/RESTORE_POINTS.md`.

### Behaviour
- Rollback is dry-run by default and requires `--execute` to restore files.
- Rollback blocks `data/books/` and `data/raw-books/` unless `--include-canonical-books` is supplied.
- Automatic restore points are created before migrations, derived artefact cleaning, human review writes and metadata enrichment writes.
- Audit entries can now include restore point IDs and rollback metadata.

## [0.47.0] - 2026-05-18

### Added
- Added durable JSONL audit log.
- Added `data/audit/bookmem.log.jsonl` as the central audit trail.
- Added `bookmem audit tail`.
- Added `bookmem audit search`.
- Added `bookmem audit export --format jsonl`.
- Added `bookmem audit export --format json`.
- Added `bookmem/audit.py`.
- Added `docs/AUDIT.md`.
- Added audit instrumentation for migrations, derived artefact cleaning, human review, setup runs and metadata enrichment.

### Behaviour
- Human review actions now write both the specialised human review log and the central audit log.
- Metadata enrichment writes provider and changed-file details when run with `--write`.
- Setup runs write a summary audit record with preset, mode and step statuses.
- Derived artefact cleaning writes deleted target information when run with `--execute`.

## [0.46.0] - 2026-05-18

### Added
- Added human review workflow for machine-generated artefacts.
- Added `bookmem review machine-drafts`.
- Added `bookmem review approve-summary <book_id>`.
- Added `bookmem review approve-concepts <book_id>`.
- Added `bookmem review reject-concept <concept_id>`.
- Added `bookmem review mark-human-reviewed <path>`.
- Added `bookmem review set-summary-status`.
- Added `bookmem review set-concepts-status`.
- Added `bookmem/human_review.py`.
- Added `docs/HUMAN_REVIEW.md`.
- Added review log at `data/review/human_review_log.jsonl`.

### Behaviour
- Supports review statuses: `machine_draft`, `needs_human_review`, `human_reviewed`, `rejected`, `superseded`.
- Summary approval updates both `book.yaml` and `chapters.yaml`.
- Concept approval updates `concepts.yaml` and syncs `data/concepts/concepts.json`.
- Rejected concepts are marked rejected rather than deleted.

## [0.45.0] - 2026-05-18

### Added
- Added generated artefact cleaner.
- Added `bookmem clean-derived`.
- Added `bookmem clean-derived --summaries`.
- Added `bookmem clean-derived --concepts`.
- Added `bookmem clean-derived --graphs`.
- Added `bookmem clean-derived --index`.
- Added `bookmem clean-derived --notes`.
- Added `bookmem clean-derived --exports`.
- Added `bookmem clean-derived --review`.
- Added `bookmem clean-derived --all --dry-run`.
- Added `bookmem/clean_derived.py`.
- Added `docs/CLEAN_DERIVED.md`.

### Behaviour
- Dry-run is the default; deletion requires `--execute`.
- `data/books/`, `data/raw-books/` and `config/` are protected and never deleted by the cleaner.
- Review queues are not included in `--all`; they require explicit `--review`.
- Derived directories are recreated with `.gitkeep` placeholders where useful.

## [0.44.0] - 2026-05-18

### Added
- Added explicit migration system.
- Added `bookmem migrations status`.
- Added `bookmem migrations apply`.
- Added `bookmem migrations create`.
- Added `bookmem/migrations.py`.
- Added `migrations/`.
- Added `migrations/0001_initial.py`.
- Added `migrations/0002_add_index_metadata.py`.
- Added `migrations/0003_add_edition_fields.py`.
- Added migration state tracking in `data/manifests/migrations.json`.
- Added `docs/MIGRATIONS.md`.

### Behaviour
- `doctor --fix` remains conservative and does not run migrations.
- Migrations are explicit, trackable and reviewable.
- Migration application supports `--dry-run`, `--target` and JSON output.

## [0.43.0] - 2026-05-18

### Added
- Added sane setup wizard re-run modes:
  - `safe`
  - `repair`
  - `rebuild`
- Added `--mode` to `bookmem setup plan`.
- Added `--mode` to `bookmem setup run`.
- Added `--force` to `bookmem setup run`.
- Added setup preflight reporting for enabled steps, long-running steps, destructive/generated rebuild steps and warnings.
- Added TUI setup mode controls for safe/repair/rebuild.
- Added setup safe-mode skipping for already-generated summaries, concepts and book graph unless `--force` is used.

### Changed
- Setup wizard is now explicitly idempotent and suitable for first-run or re-run workflows.
- CLI setup progress now updates based on completed/skipped/planned steps instead of blindly advancing all steps.
- Documentation now explains rerun behaviour and long-task status expectations.

## [0.42.0] - 2026-05-18

### Added
- Added first-run setup wizard.
- Added setup presets:
  - `full_fat`
  - `balanced`
  - `minimal`
  - `import_ready`
  - `agent_ready`
- Added `config/setup_presets.yaml`.
- Added `bookmem setup presets`.
- Added `bookmem setup status`.
- Added `bookmem setup plan`.
- Added `bookmem setup run`.
- Added `bookmem/setup_wizard.py`.
- Added `docs/SETUP_WIZARD.md`.
- Added TUI `Setup` tab with preset selection, setup plan preview, status information and streaming setup log.
- CLI setup run now uses Rich progress display with spinner, progress bar, elapsed time and rolling status line.

### Behaviour
- Setup presets use existing BookMem commands and safe doctor fixes.
- Setup does not delete books, overwrite reviewed metadata or run arbitrary shell commands.

## [0.41.0] - 2026-05-18

### Added
- Added Textual-based terminal UI.
- Added `bookmem tui`.
- Added `bookmem/tui.py`.
- Added `docs/TUI.md`.
- Added TUI views for dashboard, books, search, review queue, duplicates, system diagnostics and control panel.
- Added safe allowlisted TUI commands for doctor, doctor --fix, index-status, build-graph, retrieval evaluation, changed-only ingest and changed-only prepare-books.
- Added streaming command log for long-running control-panel tasks.
- Added `textual` dependency.

### Notes
- TUI design follows terminal-first patterns: persistent spatial layout, keyboard-first navigation, progressive help, semantic status display and safe command execution.

## [0.40.0] - 2026-05-18

### Added
- Added small local web UI.
- Added `bookmem ui`.
- Added `bookmem/web_ui.py`.
- Added `docs/WEB_UI.md`.
- Added Docker Compose service `bookmem-ui`.
- Added UI views for dashboard, books, classes, review queue, duplicates, search, topic maps, clean-check reports, system status and control panel.
- Added allowlisted UI control-panel commands for doctor, doctor --fix, index-status, build-graph and retrieval evaluation.
- Added `jinja2` dependency placeholder for web UI/template support.

### Notes
- The web UI is intended for local/trusted-network use and should be placed behind proper authentication if exposed remotely.

## [0.39.0] - 2026-05-18

### Added
- Added retrieval benchmark/evaluation set.
- Added `eval/queries.yaml`.
- Added `bookmem eval queries`.
- Added `bookmem eval retrieval`.
- Added `bookmem/evaluation.py`.
- Added `docs/EVALUATION.md`.
- Retrieval evaluation now reports Recall@K, MRR and failed queries.
- Evaluation supports custom query files, routed/non-routed search and JSON output.

### Notes
- The evaluation set is intended as a practical corpus-specific regression harness, not a formal academic IR benchmark.

## [0.38.0] - 2026-05-18

### Added
- Added embedding model management.
- Added `config/embedding_models.yaml`.
- Added `config/embedding_models.d/`.
- Added `bookmem embeddings info`.
- Added `bookmem embeddings models`.
- Added `bookmem embeddings benchmark`.
- Added `bookmem embeddings reindex`.
- Added `bookmem/embedding_management.py`.
- Added `docs/EMBEDDINGS.md`.
- Added built-in embedding profiles for default MiniLM, BGE small/base/M3 and MPNet.
- Added manifest `embedding` metadata for provider, model, dimensions, normalisation and profile.
- Added `embedding_normalised` to the index fingerprint.

### Behaviour
- `bookmem embeddings reindex --model ...` sets the active embedding model, updates manifest metadata and runs ingest.
- Raw Sentence Transformers model names can be passed directly when no named profile exists.

## [0.37.0] - 2026-05-18

### Added
- Added index/model versioning.
- Added `bookmem index-status`.
- Added `bookmem index-status --json`.
- Added `bookmem index-status --update-manifest`.
- Added `bookmem/index_versions.py`.
- Added `docs/INDEX_VERSIONING.md`.
- Added `CHUNKER_VERSION` and `INDEX_SCHEMA_VERSION`.
- Added embedding provider/model/dimension metadata helpers.
- Added manifest `index_metadata` with index schema, chunker version, embedding provider/model/dimension, cleaner version, cleaning profile, taxonomy fingerprint and BookMem version.
- Indexed book records now include the current index fingerprint.

### Behaviour
- `bookmem ingest` records the current index fingerprint after a successful ingest.
- `bookmem index-status` reports stale reasons such as changed chunker, cleaner, taxonomy or embedding model.

## [0.36.0] - 2026-05-18

### Added
- Added deterministic concept extraction.
- Added `bookmem extract-concepts`.
- Added `bookmem concepts extract-books`.
- Added `bookmem concepts rebuild-index`.
- Added `bookmem concepts search`.
- Added `bookmem concepts list`.
- Added `bookmem/concepts.py`.
- Added `data/concepts/` as the derived concept output directory.
- Added `docs/CONCEPTS.md`.
- Concepts include name, type, aliases, description, useful-for tags, source chunks, citations, confidence and review status.

### Notes
- Concept extraction output is marked `review_status: machine_draft`.
- Concepts are derived artefacts and can be rebuilt from canonical Markdown.

## [0.35.0] - 2026-05-18

### Added
- Added first-class prompt pack assets under `prompts/`.
- Added `prompts/summarise_book.md`.
- Added `prompts/generate_implementation_notes.md`.
- Added `prompts/classify_book.md`.
- Added `prompts/extract_key_models.md`.
- Added `prompts/answer_from_corpus.md`.
- Added `bookmem prompts list`.
- Added `bookmem prompts show`.
- Added `bookmem/prompt_packs.py`.
- Added `docs/PROMPT_PACKS.md`.

### Notes
- Prompts are now reusable, versioned project artefacts for Sandy, OpenClaw, Claude Code and other agents.

## [0.34.0] - 2026-05-18

### Added
- Added configurable summary providers.
- Added `config/summary_providers.yaml`.
- Added `config/summary_providers.d/`.
- Added `bookmem summary-providers`.
- Added `bookmem validate-summary-providers`.
- Added `--provider` to `bookmem summarise-book`.
- Added `--provider` to `bookmem summarise-books`.
- Added optional OpenAI summary provider.
- Added optional local Ollama summary provider.
- Added `bookmem/summary_providers.py`.
- Added `docs/SUMMARY_PROVIDERS.md`.
- Added provider/model metadata and `review_status: machine_draft` markers to summary outputs.

### Behaviour
- Deterministic summaries remain the default provider.
- LLM-assisted providers must be explicitly enabled in config.
- LLM-assisted summaries are evidence/search aids and are not marked as human-reviewed.

## [0.33.0] - 2026-05-18

### Added
- Added structured corpus answer packs.
- Added `bookmem answer-pack`.
- Added JSON output for answer packs.
- Added `bookmem/answer_pack.py`.
- Added `docs/ANSWER_PACKS.md`.
- Answer packs include route, relevant books, summary matches, top passages, read-around context, related books, suggested synthesis guidance, citations and warnings.

### Notes
- `answer-pack` prepares evidence for an agent or human. It does not generate a final prose answer locally.

## [0.32.0] - 2026-05-18

### Added
- Added derived book-to-book relationship graph.
- Added `data/graphs/book_graph.json` output.
- Added `bookmem build-graph`.
- Added `bookmem related`.
- Added `bookmem/book_graph.py`.
- Added `docs/BOOK_GRAPH.md`.
- Added graph relationship signals for shared topics, same class, routing aliases, similar summaries, same author and same work/edition group.

## [0.31.0] - 2026-05-18

### Added
- Added work and edition metadata handling.
- Added `bookmem editions`.
- Added `bookmem/editions.py`.
- Added `docs/EDITIONS.md`.
- Added frontmatter support for:
  - `work.work_id`
  - `work.canonical_title`
  - `edition.label`
  - `edition.number`
  - `edition.year`
  - `edition.is_revised`
- Added edition-aware duplicate relationship helper.

### Behaviour
- BookMem can now distinguish same ISBN duplicates from same-work different-edition records.
- Edition inference can derive simple edition labels/numbers from book titles and year from published metadata.

## [0.30.0] - 2026-05-18

### Added
- Added Open Library metadata enrichment.
- Added Google Books metadata enrichment.
- Added provider orchestration command `bookmem enrich-metadata`.
- Added `bookmem enrich-openlibrary`.
- Added `bookmem enrich-google-books`.
- Added `bookmem/metadata_enrichment.py`.
- Added `docs/METADATA_ENRICHMENT.md`.
- Added `metadata_sources` provenance tracking for enriched fields.
- Added optional `GOOGLE_BOOKS_API_KEY` support.
- Added `requests` dependency for metadata provider HTTP calls.

### Behaviour
- Enrichment fills missing fields by default.
- Existing reviewed metadata is preserved unless `--overwrite` is supplied.
- Library of Congress classification replacement still requires `--overwrite-classification`.

## [0.29.0] - 2026-05-18

### Added
- Added Calibre metadata integration.
- Added `bookmem calibre scan`.
- Added `bookmem calibre metadata`.
- Added `bookmem calibre import`.
- Added `bookmem calibre enrich`.
- Added `bookmem/calibre.py`.
- Added `docs/CALIBRE.md`.
- Added Grimmory sidecar/export integration.
- Added `bookmem grimmory sidecar`.
- Added `bookmem grimmory export`.
- Added `bookmem/grimmory.py`.
- Added `docs/GRIMMORY.md`.

### Notes
- Calibre is treated as a metadata enrichment source, not the canonical metadata store.
- Grimmory integration is file-based and exports sidecar-style JSON rather than writing directly into Grimmory's database.

## [0.28.0] - 2026-05-18

### Added
- Added import adapter command group: `bookmem import`.
- Added `bookmem import epub`.
- Added `bookmem import html`.
- Added `bookmem import pdf`.
- Added `bookmem import calibre`.
- Added `bookmem/importers.py`.
- Added `docs/IMPORT_ADAPTERS.md`.
- Added raw Markdown import frontmatter under `bookmem_import`.
- Added `pypdf` dependency for best-effort PDF text extraction.

### Notes
- Import adapters write to `data/raw-books/`.
- Canonical Markdown under `data/books/` is still produced by the existing clean/frontmatter/prepare workflow.
- Calibre import currently creates metadata stubs rather than converting ebook content.

## [0.27.0] - 2026-05-18

### Added
- Added backup and restore commands.
- Added `bookmem backup`.
- Added `bookmem restore`.
- Added `bookmem/backup.py`.
- Added `docs/BACKUP_RESTORE.md`.
- Backups include canonical books, summaries, Obsidian notes, manifests, review queues, config and project metadata.
- Backups exclude LanceDB indexes, virtual environments, caches, exports and backup archives.
- Restore supports `--dry-run`, `--overwrite`, `--target-root` and JSON output.
- Restore protects against unsafe archive paths.

## [0.26.0] - 2026-05-18

### Added
- Added optional bearer-token authentication for the local FastAPI service.
- Added `BOOKMEM_API_REQUIRE_KEY`.
- Added `BOOKMEM_API_KEY`.
- Added `bookmem serve --require-api-key`.
- Added `bookmem serve --api-key`.
- Added `docs/API_AUTH.md`.
- Added Docker Compose environment variable support for API auth.

### Changed
- API `/health` now reports whether API authentication is required.
- Protected API endpoints now require `Authorization: Bearer <token>` when API auth is enabled.

## [0.25.0] - 2026-05-18

### Added
- Added Docker support.
- Added `Dockerfile`.
- Added `docker-compose.yml`.
- Added `.dockerignore`.
- Added `docs/DOCKER.md`.
- Added Compose services:
  - `bookmem-api`
  - `bookmem-mcp`
  - `bookmem-worker`
- Added documented mounts for `./data`, `./config` and `./exports`.
- Added container health check for the FastAPI service.

## [0.24.0] - 2026-05-18

### Added
- Added `bookmem doctor` health-check command.
- Added `bookmem doctor --json` for machine-readable diagnostics.
- Added `bookmem doctor --fix` for conservative automatic repairs.
- Added `bookmem/doctor.py`.
- Added `docs/DOCTOR.md`.
- Doctor checks Python version, BookMem version, required dependencies, config files, data folders, LanceDB readability, taxonomy validity, cleaning profiles, citation styles, reference export formats, manifest readability, book counts, indexed chunks, unclassified books and review queue counts.

## [0.23.0] - 2026-05-18

### Added
- Added pytest test suite.
- Added fixture corpus under `tests/fixtures/`.
- Added tests for cleaning, cleaning profiles and clean-check reports.
- Added tests for frontmatter parsing/generation and ISBN detection.
- Added tests for BMDC classification helpers.
- Added tests for manifest records.
- Added tests for duplicate detection.
- Added tests for citation line ranges and citation formatting.
- Added tests for citation/reference exports.
- Added `docs/TESTING.md`.
- Added `pytest` to the `dev` optional dependency group.
- Added pytest configuration to `pyproject.toml`.

## [0.22.0] - 2026-05-18

### Added
- Added configurable Markdown cleaning profiles.
- Added `config/cleaning_profiles.yaml`.
- Added `config/cleaning_profiles.d/` for local profile extensions.
- Added `bookmem cleaning-profiles`.
- Added `bookmem validate-cleaning-profiles`.
- Added `--profile` support to `bookmem clean`.
- Added `--profile` support to `bookmem clean-books`.
- Added `--profile` support to `bookmem prepare-book`.
- Added `--profile` support to `bookmem prepare-books`.
- Added `docs/CLEANING_PROFILES.md`.

### Changed
- Updated Markdown cleaner to use profile-controlled cleanup options.
- Updated cleaner version to `0.2.0`.

## [0.21.0] - 2026-05-18

### Added
- Added cleaned Markdown quality checks.
- Added `bookmem/clean_check.py`.
- Added `bookmem clean-check`.
- Added JSON output for clean-check automation.
- Added CI-friendly failure flags:
  - `--fail-on-warning`
  - `--fail-on-fail`
- Added `docs/CLEAN_CHECK.md`.
- Clean checks now report remaining images, HTML, SVG/image tags, Pandoc spans, Pandoc attributes, div fences, empty anchors, raw HTML fences, EPUB artefact markers, hard-wrap splits, paragraph health, heading structure, ISBNs and frontmatter state.

## [0.20.0] - 2026-05-18

### Added
- Added Obsidian-friendly note generation.
- Added `bookmem/notes.py`.
- Added `bookmem notes` command group.
- Added `bookmem notes templates`.
- Added `bookmem notes generate`.
- Added `bookmem notes generate-books`.
- Added built-in note types:
  - `book-note`
  - `summary`
  - `implementation-notes`
- Added `config/note_templates.yaml` and `config/note_templates.d/`.
- Added `data/notes/` as the default human-facing note output directory.
- Added `docs/OBSIDIAN_NOTES.md`.

## [0.19.0] - 2026-05-18

### Added
- Added optional local FastAPI service for container-friendly integrations.
- Added `bookmem serve` CLI command.
- Added `bookmem/api.py`.
- Added HTTP endpoints:
  - `GET /health`
  - `GET /books`
  - `POST /search`
  - `POST /route`
  - `GET /chunks/{chunk_id}`
  - `GET /chunks/{chunk_id}/around`
  - `GET /chunks/{chunk_id}/section`
  - `GET /books/{book_id}/chapters`
  - `GET /books/{book_id}/chapters/{chapter}`
  - `POST /topic-map`
- Added `docs/LOCAL_API.md`.
- Added FastAPI and Uvicorn dependencies.

## [0.18.0] - 2026-05-18

### Added
- Added optional MCP server integration for MCP-capable agents.
- Added `bookmem serve-mcp` CLI command.
- Added `bookmem/mcp_server.py`.
- Exposed MCP tools:
  - `bookmem.search`
  - `bookmem.read_chunk`
  - `bookmem.read_around`
  - `bookmem.read_section`
  - `bookmem.read_chapter`
  - `bookmem.list_books`
  - `bookmem.route_query`
  - `bookmem.map_topic`
- Added `docs/MCP_SERVER.md` with client configuration examples and recommended agent workflow.
- Added `mcp>=1.2.0` optional integration dependency.

## [0.17.0] - 2026-05-18

### Added

- Added portable corpus exports for other agents and retrieval frameworks.
- Added `bookmem/agent_exports.py`.
- Added `docs/AGENT_EXPORTS.md`.
- Added `bookmem export` command with formats:
  - `jsonl`
  - `llamaindex`
  - `langchain`
  - `markdown-index`
  - `all`
- Added common agent export files:
  - `exports/bookmem_books.json`
  - `exports/bookmem_chunks.jsonl`
  - `exports/bookmem_agent_tools.md`
  - `exports/bookmem_export_manifest.json`

### Notes

- Agent exports are separate from academic reference-manager exports. They are designed for retrieval agents and framework interop.
- Chunk exports require an indexed LanceDB table. Book metadata exports can still be generated from canonical Markdown frontmatter.



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

