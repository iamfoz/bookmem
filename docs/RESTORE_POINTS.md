# Restore Points and Rollback

The audit log tells BookMem what happened. Restore points let BookMem recover
previous state.

Restore points are compressed snapshots of selected files and directories.

## Commands

Create a restore point:

```bash
bookmem restore-points create "before metadata enrichment"
```

Include canonical books and raw books explicitly:

```bash
bookmem restore-points create "full snapshot" --include-canonical-books
```

List restore points:

```bash
bookmem restore-points list
```

Show restore point contents:

```bash
bookmem restore-points show <restore_point_id>
```

Dry-run rollback:

```bash
bookmem rollback <restore_point_id>
bookmem rollback --last
```

Execute rollback:

```bash
bookmem rollback <restore_point_id> --execute
bookmem rollback --last --execute
```

Roll back using a matching audit record:

```bash
bookmem rollback --audit-id "metadata.enrich_metadata"
```

If a restore point includes canonical books, rollback is blocked unless you
explicitly allow it:

```bash
bookmem rollback <restore_point_id> --include-canonical-books --execute
```

## Storage

Restore points are stored under:

```text
data/restore-points/
  restore_points.json
  20260518T120000Z-before-metadata-enrichment.tar.gz
```

Each archive contains:

```text
restore_point.json
data/manifests/
data/summaries/
data/concepts/
data/graphs/
data/notes/
data/review/
config/
```

## Default snapshot paths

By default, restore points include:

```text
data/manifests/
data/summaries/
data/concepts/
data/graphs/
data/notes/
data/review/
config/
```

Canonical books are not included by default:

```text
data/books/
data/raw-books/
```

Add `--include-canonical-books` if you deliberately want those included.

## Usually excluded

The LanceDB index is normally excluded:

```text
data/lancedb/
```

It is generated state and can be rebuilt.

## Automatic restore points

BookMem now creates automatic restore points before higher-risk write
actions such as:

```text
migrations.apply
clean_derived --execute
human_review.*
metadata.enrich_metadata --write
```

Audit entries include rollback metadata where available:

```json
{
  "details": {
    "restore_point_id": "20260518T120000Z-before-metadata-enrichment",
    "rollback": {
      "restore_point_id": "20260518T120000Z-before-metadata-enrichment"
    }
  }
}
```

## Recommended workflow before large changes

```bash
bookmem restore-points create "before big rebuild"
bookmem clean-derived --all --execute
bookmem setup run agent_ready --mode rebuild
bookmem index-status
```

If needed:

```bash
bookmem rollback --last
bookmem rollback --last --execute
```

## Safety

Rollback uses dry-run by default.

It also blocks canonical book/raw-book restoration unless:

```bash
--include-canonical-books
```

This avoids accidental replacement of the source corpus.
