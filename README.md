# BookMem

Machine-readable Markdown book corpus for agent retrieval

BookMem turns a folder of Markdown books into a searchable, citable, agent-friendly research corpus. It cleans books, generates frontmatter, classifies them using BMDC, builds a LanceDB index, extracts summaries/concepts/claims/passages, and exposes the corpus through CLI tools, exports, a local API, MCP, Docker and Hermes-friendly workflows.

## Table of Contents

- [Background](#background)
- [Install](#install)
  - [Dependencies](#dependencies)
  - [Development install](#development-install)
  - [Docker install](#docker-install)
  - [Hermes install](#hermes-install)
- [Usage](#usage)
  - [Quick start](#quick-start)
  - [Prepare and ingest books](#prepare-and-ingest-books)
  - [Ask questions](#ask-questions)
  - [Read with citations](#read-with-citations)
  - [Summaries, concepts, claims and passages](#summaries-concepts-claims-and-passages)
  - [Workspaces, briefs and reading lists](#workspaces-briefs-and-reading-lists)
  - [Local API and MCP](#local-api-and-mcp)
  - [Profiles](#profiles)
  - [Maintenance](#maintenance)
- [Documentation](#documentation)
- [API](#api)
- [Maintainers](#maintainers)
- [Acknowledgements](#acknowledgements)
- [Contributing](#contributing)
- [License](#license)

## Background

BookMem is designed for people building personal research assistants, executive-assistant agents, note systems or local knowledge bases from a private library of books.

The core idea is simple:

```text
books as Markdown
→ cleaned canonical books
→ frontmatter and classification
→ chunks with citations
→ summaries, concepts, claims and passages
→ search, answer packs, briefs, exports, API and MCP
```

BookMem stores canonical books as Markdown because Markdown is easy to inspect, back up, diff and fix. Derived state such as summaries, graphs, review queues, passages and indexes can be regenerated.

BookMem uses BMDC, a Dewey-compatible numbering scheme with original labels and descriptions. The numbers are intended to be interoperable with common library expectations, while the taxonomy wording belongs to this project.

## Install

### Dependencies

BookMem requires:

```text
Python 3.11+
Git
pip or pipx
```

The Python package dependencies are declared in `pyproject.toml`. For embedding and indexing workflows, BookMem uses LanceDB and `sentence-transformers`.

### Development install

Clone and install:

```bash
git clone https://github.com/iamfoz/bookmem.git
cd bookmem

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Check the CLI:

```bash
bookmem --help
bookmem doctor
bookmem setup presets
bookmem setup status
```

`bookmem setup status` is passive by default. It will not download embedding models or initialise LanceDB unless you ask it to:

```bash
bookmem setup status --include-index
```

### Docker install

Build and run the API service:

```bash
docker compose up --build bookmem-api
```

Typical mounts:

```text
./data:/app/data
./config:/app/config
./exports:/app/exports
./backups:/app/backups
```

Run MCP in Docker:

```bash
docker compose up --build bookmem-mcp
```

See [docs/DOCKER.md](docs/DOCKER.md).

### Hermes install

BookMem works well as a local tool for Hermes-style agents because it exposes:

```text
CLI commands
MCP server
local FastAPI service
JSON/Markdown exports
config profiles
agent permissions
audit logs
jobs status
```

Recommended Hermes layout:

```text
~/.hermes/
  hermes-agent/
  bookmem/
    data/
    config/
    exports/
```

Install BookMem into the same Python environment Hermes can call, or expose it as a CLI command in Hermes' tool PATH:

```bash
cd ~/.hermes
git clone https://github.com/iamfoz/bookmem.git
cd bookmem

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

bookmem --profile assistant_agent doctor
```

Create or edit a Hermes tool entry that calls BookMem commands. A simple pattern is:

```yaml
tools:
  bookmem_search:
    command: /Users/YOU/.hermes/bookmem/.venv/bin/bookmem
    args:
      - --profile
      - assistant_agent
      - search
```

For MCP-capable Hermes setups:

```bash
bookmem --profile assistant_agent serve-mcp
```

For containerised Hermes setups, run the API service:

```bash
bookmem --profile docker serve --require-api-key
```

Then configure Hermes to call the local API endpoint from the same Docker network.

Recommended Hermes-safe defaults:

```bash
bookmem permissions check assistant_agent search
bookmem permissions list assistant_agent
bookmem --profile assistant_agent workspace search productivity "systems versus goals"
bookmem --profile assistant_agent answer-pack "What do my books say about systems versus goals?" --json
```

See [docs/HERMES.md](docs/HERMES.md).

## Usage

### Quick start

Run setup:

```bash
bookmem setup presets
bookmem setup run --preset balanced
```

Add Markdown books under:

```text
data/raw-books/
```

A good filename format is:

```text
<Title> - <Author> - <ISBN>.md
```

Example:

```text
Atomic Habits - James Clear - 9780735211292.md
```

Prepare and ingest:

```bash
bookmem prepare-books data/raw-books --changed-only
bookmem ingest --changed-only
```

Search:

```bash
bookmem search "systems versus goals"
```

Build an answer pack:

```bash
bookmem answer-pack "What do my books say about systems versus goals?" --json
```

### Prepare and ingest books

Clean a book:

```bash
bookmem clean "data/raw-books/Book.md" --profile epub_pandoc
```

Check the cleaned Markdown:

```bash
bookmem clean-check "data/raw-books/Book.md"
```

Generate or update frontmatter:

```bash
bookmem frontmatter "data/raw-books/Book.md" --write
```

Prepare books into canonical structure:

```bash
bookmem prepare-books data/raw-books --changed-only
```

Ingest into LanceDB:

```bash
bookmem ingest --changed-only
```

Reset and rebuild the index:

```bash
bookmem ingest --reset
```

### Ask questions

Search the whole corpus:

```bash
bookmem search "compound interest"
```

Route a query:

```bash
bookmem route "What do my books say about compound interest?"
```

Use routed search and context assembly:

```bash
bookmem ask-search "What do my books say about compound interest?"
```

Build a structured answer pack:

```bash
bookmem answer-pack "What do my books say about risk and return?"
bookmem answer-pack "What do my books say about risk and return?" --json
```

### Read with citations

Read a chunk:

```bash
bookmem read-section --chunk-id <chunk_id>
```

Read around a chunk:

```bash
bookmem read-around <chunk_id> --before 2 --after 3
```

Read a chapter:

```bash
bookmem read-chapter --book <book_id> --chapter "Chapter 6"
```

Search results include source information such as title, author, chapter/heading path, line range and chunk ID.

### Summaries, concepts, claims and passages

Generate summaries:

```bash
bookmem summarise-books data/books --provider deterministic
bookmem search-summaries "systems versus goals"
```

Extract concepts:

```bash
bookmem extract-concepts "data/books/.../Book.md"
bookmem concepts search "circle of influence"
```

Extract claims:

```bash
bookmem extract-claims "data/books/.../Book.md"
bookmem claims search "goals"
bookmem claims compare "compound interest"
```

Extract useful passages:

```bash
bookmem passages extract "data/books/.../Book.md"
bookmem passages search "energy management"
bookmem passages favourite <chunk_id>
bookmem passages export --format obsidian --output exports/commonplace.md
```

### Workspaces, briefs and reading lists

List workspaces:

```bash
bookmem workspace list
```

Search a workspace:

```bash
bookmem workspace search productivity "systems versus goals"
bookmem workspace answer-pack finance "risk and return" --json
```

Save a recurring query:

```bash
bookmem query save "systems versus goals" --name systems-goals --workspace productivity
bookmem brief generate systems-goals
```

Generate a reading list:

```bash
bookmem reading-list --topic "personal finance for beginners"
bookmem reading-list --goal "build an executive assistant agent"
```

### Local API and MCP

Run the local API:

```bash
bookmem serve --host 127.0.0.1 --port 8765
```

Require an API key:

```bash
BOOKMEM_API_KEY="change-me" bookmem serve --require-api-key
```

Run MCP:

```bash
bookmem serve-mcp
```

### Profiles

Use a profile for one command:

```bash
bookmem --profile assistant_agent search "systems thinking"
bookmem --profile docker serve
```

Persist a profile:

```bash
bookmem profile use assistant_agent
bookmem profile current
```

Built-in profiles:

```text
local
docker
assistant_agent
```

### Maintenance

Run health checks:

```bash
bookmem doctor
bookmem doctor --deep
```

Inspect jobs:

```bash
bookmem jobs list
bookmem jobs status <job_id>
bookmem jobs tail <job_id>
```

Back up and restore:

```bash
bookmem backup --output backups/bookmem-$(date +%Y-%m-%d).tar.gz
bookmem restore backups/bookmem-2026-05-22.tar.gz
```

Export graph visualisations:

```bash
bookmem graph export --format all
```


## Documentation

Start here:

- [Documentation index](docs/README.md)
- [Quick start](docs/QUICKSTART.md)
- [Installation](docs/INSTALL.md)
- [Hermes integration](docs/HERMES.md)
- [Command reference](docs/COMMAND_REFERENCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## API

BookMem is mainly a CLI application, but the package modules are importable. The most stable integration points are:

```text
bookmem search ...
bookmem answer-pack ...
bookmem workspace answer-pack ...
bookmem serve
bookmem serve-mcp
bookmem export --format jsonl
```

For programmatic integration, prefer the local API, MCP server or JSON CLI output until the Python API stabilises.

## Maintainers

- Martyn Forryan

## Acknowledgements

BookMem is inspired by practical agent-memory and retrieval workflows, and acknowledges a debt of gratitude to the MIT-licensed CortexReach `memory-lancedb-pro` project as an important source of ideas for LanceDB-backed memory/retrieval design.

## Contributing

Issues and pull requests are welcome once the public repository is available.

Before contributing:

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
bookmem doctor
```

Please keep documentation updated with code changes and avoid committing generated indexes, private books, secrets or local data.

## License

GPL-3.0-only © Martyn Forryan
