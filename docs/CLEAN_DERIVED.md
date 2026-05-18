# Generated Artefact Cleaner

BookMem generates many derived artefacts:

```text
summaries
concepts
graphs
LanceDB indexes
Obsidian notes
exports
review queues
```

`bookmem clean-derived` provides a safe way to clean generated state before a
rebuild.

## Safety rules

The cleaner must never delete:

```text
data/books/
data/raw-books/
config/
```

Review queues are also protected from `--all` and are cleaned only when
`--review` is explicitly supplied.

Dry-run is the default.

## Commands

Preview all generated artefacts except review queues:

```bash
bookmem clean-derived --all --dry-run
```

Execute deletion:

```bash
bookmem clean-derived --all --execute
```

Clean summaries:

```bash
bookmem clean-derived --summaries
bookmem clean-derived --summaries --execute
```

Clean concepts:

```bash
bookmem clean-derived --concepts
bookmem clean-derived --concepts --execute
```

Clean graphs:

```bash
bookmem clean-derived --graphs
bookmem clean-derived --graphs --execute
```

Clean LanceDB index:

```bash
bookmem clean-derived --index
bookmem clean-derived --index --execute
```

Clean notes and exports:

```bash
bookmem clean-derived --notes --exports --execute
```

Clean review queues explicitly:

```bash
bookmem clean-derived --review --execute
```

Clean everything including review queues:

```bash
bookmem clean-derived --all --review --execute
```

JSON output:

```bash
bookmem clean-derived --all --dry-run --json
```

## Targets

```text
--summaries  data/summaries/
--concepts   data/concepts/
--graphs     data/graphs/
--index      data/lancedb/
--notes      data/notes/
--exports    exports/
--review     data/review/ only when explicit
```

## Pairing with setup rebuild mode

This pairs well with the setup wizard:

```bash
bookmem backup --output backups/pre-rebuild.tar.gz
bookmem clean-derived --all --dry-run
bookmem clean-derived --all --execute
bookmem setup run agent_ready --mode rebuild
```

## Recommended cautious rebuild flow

```bash
bookmem doctor
bookmem backup --output backups/pre-clean-derived.tar.gz
bookmem clean-derived --all --dry-run
bookmem clean-derived --all --execute
bookmem setup run balanced --mode rebuild
bookmem index-status
```

## What gets recreated

Some derived folders are recreated with `.gitkeep` placeholders after
deletion:

```text
data/summaries/
data/concepts/
data/graphs/
data/notes/
data/review/
```

`data/lancedb/` and `exports/` are recreated when the relevant commands run.
