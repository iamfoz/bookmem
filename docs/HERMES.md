# Hermes Integration

BookMem can be used by Hermes as a command-line tool, local API or MCP server.

## Recommended layout

```text
~/.hermes/
  hermes-agent/
  bookmem/
    data/
    config/
    exports/
```

## Install

```bash
cd ~/.hermes
git clone https://github.com/iamfoz/bookmem.git
cd bookmem

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Check:

```bash
bookmem --profile assistant_agent doctor
bookmem --profile assistant_agent workspace list
```

## CLI tool pattern

Configure Hermes to call the BookMem executable with the agent profile:

```yaml
tools:
  bookmem_search:
    command: /Users/YOU/.hermes/bookmem/.venv/bin/bookmem
    args:
      - --profile
      - assistant_agent
      - search
```

Useful CLI calls for Hermes:

```bash
bookmem --profile assistant_agent search "systems thinking" --json
bookmem --profile assistant_agent answer-pack "What do my books say about goals?" --json
bookmem --profile assistant_agent workspace answer-pack productivity "systems versus goals" --json
bookmem --profile assistant_agent claims compare "compound interest" --json
```

## MCP mode

Start the MCP server:

```bash
bookmem --profile assistant_agent serve-mcp
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
BOOKMEM_API_KEY="change-me" bookmem --profile assistant_agent serve --require-api-key
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

For Hermes, prefer commands that return JSON and avoid destructive actions unless
the user explicitly asks.

Recommended agent-safe commands:

```bash
bookmem search "..." --json
bookmem answer-pack "..." --json
bookmem workspace answer-pack productivity "..." --json
bookmem reading-list --goal "..." --json
bookmem jobs status <job_id> --json
```
