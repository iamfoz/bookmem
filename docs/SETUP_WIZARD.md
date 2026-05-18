# Setup Wizard

BookMem includes a first-run setup wizard for getting from a fresh checkout
to a usable corpus workflow.

The wizard is available from both the CLI and the TUI.

## Presets

Presets live in:

```text
config/setup_presets.yaml
```

Built-in presets:

```text
full_fat      Generate everything: prepare, ingest, summaries, concepts, graph, eval and status.
balanced      Recommended first run for most users.
minimal       Create folders and validate setup only.
import_ready  Prepare the project for EPUB/PDF/Calibre imports.
agent_ready   Build agent-facing artefacts such as summaries, concepts and graph.
```

## CLI commands

List presets:

```bash
bookmem setup presets
```

Show current setup status:

```bash
bookmem setup status
```

Show the plan for a preset:

```bash
bookmem setup plan balanced
```

Dry run:

```bash
bookmem setup run balanced --dry-run
```

Run setup:

```bash
bookmem setup run balanced
```

Full-fat setup:

```bash
bookmem setup run full_fat
```

JSON output:

```bash
bookmem setup run agent_ready --json
```

## TUI setup wizard

Run:

```bash
bookmem tui
```

Open the `Setup` tab.

The setup tab includes:

```text
preset list
setup status panel
plan preview
long-task log
preset buttons
```

Preset buttons:

```text
Use full_fat
Use balanced
Use minimal
Use import_ready
Use agent_ready
```

## Status feedback

CLI setup uses Rich progress display:

```text
spinner
progress bar
elapsed time
rolling status line
```

TUI setup uses:

```text
persistent setup tab
plan preview
streaming setup log
refreshed dashboard/system state after completion
```

## Preset behaviour

### `minimal`

```text
create required directories
validate config/environment
apply safe doctor fixes
check index status
```

### `balanced`

```text
create required directories
validate config/environment
apply safe doctor fixes
prepare changed raw books
ingest changed books
generate deterministic summaries
build relationship graph
check index status
```

### `full_fat`

```text
everything in balanced
extract concepts
run retrieval evaluation
additional quality-check hooks
```

### `import_ready`

```text
create directories
validate config/environment
apply safe doctor fixes
prepare the raw-book/import workflow
```

### `agent_ready`

```text
prepare changed raw books
ingest changed books
generate summaries
extract concepts
build graph
run retrieval evaluation
check index status
```

## Safety

Setup uses existing BookMem commands and safe doctor fixes.

It does not delete books, overwrite reviewed frontmatter, clear review
queues or run arbitrary shell commands.

## Custom presets

Add or edit presets in:

```text
config/setup_presets.yaml
```

Preset shape:

```yaml
setup_presets:
  my_preset:
    label: My Preset
    description: What this preset does.
    actions:
      create_dirs: true
      validate_config: true
      doctor_fix: true
      prepare_changed_only: true
      summarise: true
      extract_concepts: false
      build_graph: true
      eval_retrieval: false
      index_status: true
    summary_provider: deterministic
    embedding_profile: default
```


## Re-running setup

The wizard is designed to be safe to run on an existing BookMem setup.

Rerun modes:

```text
safe     Default. Uses changed-only operations and skips expensive generated artefacts when they already exist.
repair   Runs validation/fix steps and enabled workflow steps without intentionally resetting generated indexes.
rebuild  Recreates generated artefacts where appropriate, including index reset/rebuild behaviour.
```

CLI examples:

```bash
bookmem setup run balanced
bookmem setup run balanced --mode safe
bookmem setup run balanced --mode repair
bookmem setup run agent_ready --mode rebuild
```

Force safe mode to run steps it would normally skip:

```bash
bookmem setup run full_fat --mode safe --force
```

Dry-run an existing setup:

```bash
bookmem setup run agent_ready --mode rebuild --dry-run
```

The TUI Setup tab also exposes the same modes:

```text
Mode: safe
Mode: repair
Mode: rebuild
```

## Long-running task feedback

Any setup path that can take more than a couple of seconds should expose
visible status.

CLI setup uses:

```text
spinner
progress bar
elapsed time
rolling status line
per-step status
```

TUI setup uses:

```text
fixed Setup tab
current preset/mode display
plan preview
streaming log output
dashboard refresh after completion
```

Long-running setup steps are explicitly marked in the plan:

```text
prepare changed raw books
ingest changed books
generate summaries
extract concepts
```

This makes first-run and re-run behaviour predictable rather than opaque.
