# Operations

## Health checks

```bash
bookmem doctor
bookmem doctor --deep
```

Use `--deep` for integrity checks across chunks, citations, manifests, summaries,
concepts, graphs, embeddings, review queues and config.

## Jobs

```bash
bookmem jobs list
bookmem jobs status <job_id>
bookmem jobs tail <job_id>
```

Jobs are stored under:

```text
data/jobs/
```

## Audit

```bash
bookmem audit tail
bookmem audit search "enrich"
bookmem audit export --format jsonl
```

## Backups

```bash
bookmem backup --output backups/bookmem-$(date +%Y-%m-%d).tar.gz
bookmem restore backups/bookmem-2026-05-22.tar.gz
```

Backups should include canonical books, summaries, notes, manifests, review queues,
config and changelog. Indexes and exports can usually be regenerated.

## Migrations

```bash
bookmem migrations status
bookmem migrations apply
bookmem migrations create "add new field"
```

Do not silently run migrations from `doctor --fix`.

## Derived cleanup

```bash
bookmem clean-derived --all --dry-run
bookmem clean-derived --summaries
bookmem clean-derived --index
```

Never delete canonical books with derived cleanup.
