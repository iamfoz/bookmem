# Docker

BookMem includes Docker support for running the local API and optional MCP
server beside other agent infrastructure.

The container does not make Markdown, LanceDB or configuration canonical.
Those remain mounted from the host:

```text
./data:/app/data
./config:/app/config
./exports:/app/exports
```

## Files

```text
Dockerfile
docker-compose.yml
.dockerignore
docs/DOCKER.md
```

## Build

```bash
docker compose build
```

## Run the local API

```bash
docker compose up -d bookmem-api
```

The API listens on:

```text
http://localhost:8765
```

OpenAPI docs:

```text
http://localhost:8765/docs
```

Health check:

```bash
curl http://localhost:8765/health
```

## Run one-off commands in Docker

Use the `bookmem-worker` service for CLI commands:

```bash
docker compose run --rm bookmem-worker bookmem doctor
docker compose run --rm bookmem-worker bookmem doctor --fix
docker compose run --rm bookmem-worker bookmem status
docker compose run --rm bookmem-worker bookmem ingest --changed-only
docker compose run --rm bookmem-worker bookmem prepare-books data/raw-books --changed-only
```

## Run MCP server

The MCP server communicates over stdio, so it is normally run directly by the
MCP client. A compose profile is provided for environments that need it:

```bash
docker compose --profile mcp run --rm bookmem-mcp
```

For most MCP clients, point the client at Docker:

```json
{
  "mcpServers": {
    "bookmem": {
      "command": "docker",
      "args": [
        "compose",
        "--profile",
        "mcp",
        "run",
        "--rm",
        "bookmem-mcp"
      ],
      "cwd": "/path/to/bookmem"
    }
  }
}
```

Or run the project virtual environment directly:

```json
{
  "mcpServers": {
    "bookmem": {
      "command": "/path/to/bookmem/.venv/bin/bookmem",
      "args": ["serve-mcp"],
      "cwd": "/path/to/bookmem"
    }
  }
}
```

## Volumes

The compose file mounts:

```yaml
volumes:
  - ./data:/app/data
  - ./config:/app/config
  - ./exports:/app/exports
```

This means all important corpus state remains on the host.

## Environment variables

Default container environment:

```text
BOOKMEM_BOOKS_DIR=/app/data/books
BOOKMEM_DB_DIR=/app/data/lancedb
BOOKMEM_TABLE=book_chunks
BOOKMEM_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

You can override these in `docker-compose.yml` or a Compose override file.

## First run

```bash
docker compose build
docker compose run --rm bookmem-worker bookmem doctor --fix
docker compose run --rm bookmem-worker bookmem prepare-books data/raw-books --changed-only
docker compose run --rm bookmem-worker bookmem summarise-books data/books
docker compose run --rm bookmem-worker bookmem ingest --changed-only
docker compose up -d bookmem-api
```

## Rebuild after upgrades

```bash
docker compose build --no-cache
docker compose run --rm bookmem-worker bookmem doctor
docker compose run --rm bookmem-worker bookmem ingest --changed-only
docker compose up -d bookmem-api
```

If the schema has changed, run:

```bash
docker compose run --rm bookmem-worker bookmem ingest --reset
```

## Notes on `.dockerignore`

`.dockerignore` excludes generated or potentially large data directories such
as `data/books`, `data/raw-books`, `data/lancedb`, `exports` and backups.
These are mounted at runtime rather than baked into the image.

## Security

The API is intended for local or trusted-network use. By default it binds to
`0.0.0.0` inside the container and maps to host port `8765`.

If exposing outside localhost or a trusted internal Docker network, place it
behind your existing reverse proxy/auth layer or add API authentication.
