# Migrations

BookMem includes an explicit migration system for schema and persisted-data
upgrades.

This is deliberately separate from `bookmem doctor --fix`.

```text
doctor     diagnoses and performs conservative repairs
migrations change persisted schema/metadata/data shape
```

## Commands

Show migration status:

```bash
bookmem migrations status
```

JSON:

```bash
bookmem migrations status --json
```

Show pending migrations without applying:

```bash
bookmem migrations apply --dry-run
```

Apply pending migrations:

```bash
bookmem migrations apply
```

Apply up to a target migration:

```bash
bookmem migrations apply --target 0002_add_index_metadata
```

Create a new migration:

```bash
bookmem migrations create "add concept review status"
```

This creates:

```text
migrations/0004_add_concept_review_status.py
```

## Migration files

Migrations live in:

```text
migrations/
  0001_initial.py
  0002_add_index_metadata.py
  0003_add_edition_fields.py
```

Each migration file declares:

```python
ID = "0002_add_index_metadata"
DESCRIPTION = "Add manifest-level index metadata placeholder."
VERSION = 1

def apply(context: dict[str, Any]) -> dict[str, Any]:
    ...
```

## State file

Applied migrations are tracked in:

```text
data/manifests/migrations.json
```

Example:

```json
{
  "schema_version": 1,
  "migration_system_version": "0.1.0",
  "applied": [
    {
      "id": "0001_initial",
      "path": "migrations/0001_initial.py",
      "description": "Initial migration baseline and manifest structure.",
      "applied_at": "2026-05-18T12:00:00+00:00",
      "result": {}
    }
  ]
}
```

## Built-in migrations

### `0001_initial`

Ensures the core manifest directory and `data/manifests/books.json` exist.

### `0002_add_index_metadata`

Adds a manifest-level `index_metadata` placeholder for older installs.

After this migration, run one of:

```bash
bookmem ingest --changed-only
bookmem index-status --update-manifest
```

### `0003_add_edition_fields`

Adds safe `work` and `edition` placeholders to canonical book frontmatter
where missing.

It does not overwrite existing `work` or `edition` blocks.

For richer inference, run:

```bash
bookmem editions --write
```

## Rules for writing migrations

Good migrations should be:

```text
explicit
idempotent where practical
conservative with human-reviewed metadata
clear about generated versus canonical data
small enough to review
```

Avoid:

```text
deleting canonical books
silently overwriting human-reviewed metadata
doing expensive reindexing without saying so
hiding schema changes inside doctor --fix
```

## Recommended upgrade flow

```bash
git pull
bookmem migrations status
bookmem migrations apply --dry-run
bookmem backup --output backups/pre-migration.tar.gz
bookmem migrations apply
bookmem doctor
bookmem index-status
```

If migrations indicate index/schema changes:

```bash
bookmem ingest --reset
```
