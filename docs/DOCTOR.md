# Doctor

`bookmem doctor` runs a health check over the local BookMem installation.

It is designed for use after upgrades, before exposing BookMem to an assistant agent, and
when diagnosing indexing/retrieval problems.

## Run

```bash
bookmem doctor
```

JSON output:

```bash
bookmem doctor --json
```

## Safe automatic fixes

```bash
bookmem doctor --fix
```

`--fix` is deliberately conservative. It may:

```text
create missing data directories
add .gitkeep placeholders
create an empty manifest if none exists
create placeholder config files when missing
```

It will not:

```text
reclassify books
overwrite reviewed metadata
delete files
rewrite LanceDB indexes
clear review queues
silently repair broken config content
```

## Checks

Doctor currently checks:

```text
Python version
BookMem version
Required dependencies
Config files present
Data folders present
LanceDB readable
Taxonomy valid
Cleaning profiles valid
Citation styles valid
Reference export formats valid
Manifest readable
Number of books
Number of indexed chunks
Unclassified count
Review queue count
```

## Example output

```text
BookMem 0.24.0
Python: 3.12.3

Environment: OK
Dependencies: OK
Config: OK
Data folders: OK
Taxonomy: OK
Cleaning profiles: OK
Citation styles: OK
Reference formats: OK
Manifest: OK
LanceDB: OK

Books: 214
Indexed chunks: 18,420
Needs review: 7
Unclassified: 3

Status: WARN
Reason:
- 7 review item(s) need attention.
- 3 unclassified book(s).
```

## Exit codes

`bookmem doctor` exits non-zero when the overall status is `FAIL`.

`WARN` is intended to be visible but not fatal. Examples include review items
or unclassified books.


## Doctor and migrations

Migrations are not run by doctor.

`bookmem doctor --fix` is limited to conservative repairs such as
creating missing folders, placeholder files or an empty manifest. It does
not apply schema/data migrations.

Use:

```bash
bookmem migrations status
bookmem migrations apply
```

See `docs/MIGRATIONS.md`.
