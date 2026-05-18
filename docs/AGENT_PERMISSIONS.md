# Agent Permissions

BookMem includes a declarative safety policy for agents.

Before Sandy or another agent performs an action, it can ask BookMem whether
that action is allowed, requires confirmation or is denied.

## Policy file

```text
config/agent_permissions.yaml
```

Example:

```yaml
agents:
  sandy:
    allow:
      - search
      - read
      - answer_pack
      - related
      - concepts.search

    require_confirmation:
      - enrich_metadata.write
      - prepare_books
      - ingest_reset
      - restore

    deny:
      - delete_canonical_books
      - overwrite_human_reviewed_metadata
```

## Commands

Check one permission:

```bash
bookmem permissions check sandy enrich_metadata.write
```

List effective permissions for an agent:

```bash
bookmem permissions list sandy
```

List configured agents:

```bash
bookmem permissions agents
```

Validate policy:

```bash
bookmem permissions validate
```

JSON mode:

```bash
bookmem permissions check sandy answer_pack --json
bookmem permissions list sandy --json
```

## Decisions

Permission checks return one of:

```text
allow
require_confirmation
deny
unknown
```

Resolution order:

```text
1. deny
2. require_confirmation
3. allow
4. unknown
```

Deny always wins.

Unknown should be treated as not allowed until configured.

## Exit codes

`bookmem permissions check` uses exit codes suitable for scripts and agents:

```text
0  allowed
2  denied or unknown
3  requires confirmation
```

## Built-in profiles

### `sandy`

Primary executive-assistant agent profile. Can search/read/answer, but
requires confirmation for writes, rebuilds, migrations, rollback and review
actions.

### `readonly`

Search and evidence-pack only. Good for untrusted agents.

### `admin`

Human/admin profile. Broadly allowed, but still denies arbitrary shell.

## Useful action names

Read/search actions:

```text
search
read
route_query
list_books
search_summaries
answer_pack
related
map_topic
concepts.search
concepts.list
prompts.list
prompts.show
```

Write/rebuild actions:

```text
enrich_metadata.write
prepare_books
ingest_changed_only
ingest_reset
summarise
extract_concepts
build_graph
clean_derived.execute
migrations.apply
restore_points.create
rollback.dry_run
rollback.execute
review.approve
review.reject
```

Dangerous/sensitive actions:

```text
delete_canonical_books
delete_raw_books
overwrite_human_reviewed_metadata
restore.include_canonical_books
arbitrary_shell
```

## Wildcards

Rules support simple shell-style wildcards:

```yaml
allow:
  - concepts.*
  - prompts.*

deny:
  - "*.execute"
```

## Suggested agent behaviour

Agents should check permissions before significant actions:

```bash
bookmem permissions check sandy answer_pack
bookmem permissions check sandy enrich_metadata.write
```

If the decision is `require_confirmation`, the agent should ask the user
before continuing.

If the decision is `deny` or `unknown`, the agent should not proceed.

## Relationship to audit and restore points

Permissions decide whether an agent may act.

Audit records what happened.

Restore points allow recovery.

Use all three together for serious agent infrastructure:

```text
permissions -> action -> restore point -> audit log -> user report
```
