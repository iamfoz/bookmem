# Hermes Integration

BookMem can be used by Hermes as a command-line tool, local API or MCP server.

## Two ways to run BookMem

BookMem supports two modes:

- Standalone: clone the repo, install it, and use the local `./data` and
  `./config` directories from the project directory. This is the default and is
  unchanged.
- Hermes: the BookMem package is installed into the Hermes agent virtualenv
  (`~/.hermes/hermes-agent/venv`), while runtime data and config live separately
  under `~/.hermes/bookmem`. There is no separate BookMem virtualenv, and the
  repo checkout is not needed as the working directory at runtime.

This guide covers the Hermes mode.

## Recommended layout

```text
~/.hermes/
  hermes-agent/
    venv/                 BookMem package installed here
  bin/
    bookmem               optional wrapper
  bookmem/                runtime home (BOOKMEM_HOME)
    config/
    data/
    exports/
    backups/
    logs/
```

The repo itself is cloned separately, conventionally to `~/code/bookmem`. It is
only needed to install or update the package.

## Runtime root

BookMem resolves a runtime root and, when that root is explicit, makes it the
working directory so that `data/`, `config/`, `exports/`, `backups/` and
`logs/` all resolve under it.

The runtime root is resolved with this precedence:

```text
1. --home PATH command-line option
2. BOOKMEM_HOME environment variable
3. the selected profile's paths.home_dir
4. Hermes auto-detection (interpreter running inside
   ~/.hermes/hermes-agent/venv)
5. the current working directory (standalone fallback)
```

In Hermes mode the root is `~/.hermes/bookmem`. The `hermes` profile sets it
through `paths.home_dir`, and the wrapper installed by
`bookmem hermes install-wrapper` sets it through `BOOKMEM_HOME`. When BookMem
runs from inside the Hermes venv, step 4 also detects it automatically.

Standalone usage is unchanged: relative `./data` and `./config` resolve from
the current directory.

See [Configuration](CONFIGURATION.md) for more on `BOOKMEM_HOME` and the
runtime root.

## Install

Clone the repo:

```bash
git clone https://github.com/iamfoz/bookmem.git ~/code/bookmem
cd ~/code/bookmem
```

Install the BookMem package into the Hermes agent virtualenv:

```bash
$HOME/.hermes/hermes-agent/venv/bin/python -m pip install -U .
```

For an editable development install:

```bash
$HOME/.hermes/hermes-agent/venv/bin/python -m pip install -U -e .
```

The `python -m pip` form is preferred because it guarantees pip runs in the
intended interpreter. If a pip executable exists directly,
`$HOME/.hermes/hermes-agent/venv/bin/pip install -U .` is also acceptable.

This installs the BookMem Python package into the Hermes venv. It does not
place runtime data inside the venv, and it does not create a separate
virtualenv. Runtime data goes under `~/.hermes/bookmem`.

To print these install commands at any time:

```bash
$HOME/.hermes/hermes-agent/venv/bin/bookmem hermes install-help
```

## Initialise the runtime home

Create `~/.hermes/bookmem` and its subdirectories and copy the default config:

```bash
$HOME/.hermes/hermes-agent/venv/bin/bookmem hermes init
```

`hermes init` is idempotent and supports `--dry-run`, `--force` and `--json`.

The runtime home `~/.hermes/bookmem/` has this layout:

```text
config/
data/
  raw-books
  books
  lancedb
  manifests
  summaries
  review
  graphs
  concepts
  claims
  passages
  queries
  briefs
  reading-lists
  jobs
  audit
  notes
exports/
backups/
logs/
```

## Install the wrapper

Optionally install a wrapper at `~/.hermes/bin/bookmem`:

```bash
$HOME/.hermes/hermes-agent/venv/bin/bookmem hermes install-wrapper
```

The wrapper sets `BOOKMEM_HOME` and runs `bookmem --profile hermes` via the
Hermes venv, so Hermes can call a single stable path. It supports `--dry-run`,
`--force` and `--json`.

Once the wrapper exists, configure Hermes to call `~/.hermes/bin/bookmem`.

## Check the install

```bash
bookmem --profile hermes hermes status
bookmem --profile hermes workspace list
```

`bookmem hermes status` is a passive Hermes health check. It does not load
embedding models, initialise LanceDB or contact Hugging Face. It supports
`--json`.

## Add books

Put Markdown books under:

```text
~/.hermes/bookmem/data/raw-books/
```

Then prepare and ingest with the `hermes` profile:

```bash
bookmem --profile hermes prepare-books data/raw-books --changed-only
bookmem --profile hermes ingest --changed-only
```

## CLI tool pattern

Configure Hermes to call the wrapper:

```yaml
tools:
  bookmem_search:
    command: /Users/YOU/.hermes/bin/bookmem
    args:
      - search
```

If you prefer not to install the wrapper, call the venv executable directly and
pass the profile yourself:

```yaml
tools:
  bookmem_search:
    command: /Users/YOU/.hermes/hermes-agent/venv/bin/bookmem
    args:
      - --profile
      - hermes
      - search
```

Useful CLI calls for Hermes:

```bash
bookmem --profile hermes search "systems thinking" --json
bookmem --profile hermes answer-pack "What do my books say about goals?" --json
bookmem --profile hermes workspace answer-pack productivity "systems versus goals" --json
bookmem --profile hermes claims compare "compound interest" --json
```

## Hermes commands

The `hermes` command group manages the Hermes runtime home and wrapper:

```bash
bookmem hermes init             create ~/.hermes/bookmem and subdirs, copy config
bookmem hermes status           passive Hermes health check
bookmem hermes install-wrapper  create the ~/.hermes/bin/bookmem wrapper
bookmem hermes install-help     print the canonical install commands
```

`hermes init` and `hermes install-wrapper` support `--dry-run`, `--force` and
`--json`. `hermes status` supports `--json`.

## MCP mode

Start the MCP server:

```bash
bookmem --profile hermes serve-mcp
```

Expose these tools to Hermes where supported:

```text
bookmem.search
bookmem.read_chunk
bookmem.read_chapter
bookmem.list_books
bookmem.route_query
bookmem.map_topic
```

## API mode

Start the API:

```bash
BOOKMEM_API_KEY="change-me" bookmem --profile hermes serve --require-api-key
```

In Docker:

```bash
docker compose up --build bookmem-api
```

## Permissions

Check what an agent can do:

```bash
bookmem permissions list assistant_agent
bookmem permissions check assistant_agent search
bookmem permissions check assistant_agent prepare_books
```

Recommended baseline:

```text
Allow search, read, answer packs, related books and concept search.
Require confirmation for metadata writes, prepare, ingest reset and restore.
Deny deleting canonical books and overwriting human-reviewed metadata.
```

## Operational safety

For Hermes, prefer commands that return JSON and avoid destructive actions
unless the user explicitly asks.

`bookmem hermes status`, `bookmem setup status` and
`bookmem --profile hermes setup status` are all passive: they do not load
sentence-transformers, initialise LanceDB, contact Hugging Face or download
embedding models.

Recommended agent-safe commands:

```bash
bookmem --profile hermes search "..." --json
bookmem --profile hermes answer-pack "..." --json
bookmem --profile hermes workspace answer-pack productivity "..." --json
bookmem --profile hermes reading-list --goal "..." --json
bookmem --profile hermes jobs status <job_id> --json
```
