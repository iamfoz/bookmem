# Backup and Restore

BookMem can create and restore portable `.tar.gz` backups of canonical and
reviewable project state.

The backup command deliberately excludes rebuildable/generated-heavy data
such as LanceDB indexes and export artefacts.

## Create a backup

```bash
bookmem backup --output backups/bookmem-2026-05-18.tar.gz
```

Overwrite an existing backup:

```bash
bookmem backup --output backups/bookmem-2026-05-18.tar.gz --overwrite
```

JSON output:

```bash
bookmem backup --output backups/bookmem-2026-05-18.tar.gz --json
```

## Restore a backup

```bash
bookmem restore backups/bookmem-2026-05-18.tar.gz
```

Dry run first:

```bash
bookmem restore backups/bookmem-2026-05-18.tar.gz --dry-run
```

Restore into another directory:

```bash
bookmem restore backups/bookmem-2026-05-18.tar.gz --target-root /tmp/bookmem-restore
```

Overwrite existing files:

```bash
bookmem restore backups/bookmem-2026-05-18.tar.gz --overwrite
```

## Included by default

```text
data/books/
data/summaries/
data/notes/
data/manifests/
data/review/
config/
CHANGELOG.md
README.md
pyproject.toml
LICENSE
AUTHORS.md
NOTICE
```

## Excluded by default

```text
data/lancedb/
.venv/
venv/
__pycache__/
exports/
backups/
.git/
cache directories
```

## Why exclude LanceDB?

`data/lancedb/` is a generated retrieval index. It can be rebuilt from the
canonical Markdown and metadata:

```bash
bookmem ingest --reset
```

Excluding LanceDB makes backups smaller, more portable and less tied to a
particular index schema or embedding model.

## Recommended recovery flow

```bash
bookmem restore backups/bookmem-2026-05-18.tar.gz
bookmem doctor --fix
bookmem ingest --reset
bookmem status
```

## Safety

Restore protects against path traversal inside backup archives.

Existing files are skipped unless `--overwrite` is supplied.
