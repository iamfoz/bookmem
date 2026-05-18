# Local HTTP API

BookMem includes an optional FastAPI service for local and container-based
integrations. It exposes the same corpus search, routing and reading
capabilities as the CLI and MCP server over HTTP.

## Start the API

```bash
bookmem serve
```

By default the service binds to:

```text
http://127.0.0.1:8765
```

Custom host/port:

```bash
bookmem serve --host 0.0.0.0 --port 8765
```

Development reload mode:

```bash
bookmem serve --reload
```

## OpenAPI docs

Once running, visit:

```text
http://127.0.0.1:8765/docs
```

## Endpoints

### `GET /health`

Returns service health and version.

```bash
curl http://127.0.0.1:8765/health
```

### `GET /books`

List canonical books discovered from Markdown frontmatter.

Query parameters:

```text
class_code: optional BMDC class filter
author: optional author substring filter
limit: default 100, max 500
```

Example:

```bash
curl "http://127.0.0.1:8765/books?class_code=332"
```

### `POST /search`

Search indexed chunks.

Example:

```bash
curl -X POST http://127.0.0.1:8765/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "compound interest",
    "aliases": ["finance"],
    "limit": 8,
    "mode": "hybrid",
    "include_text": false
  }'
```

Request fields:

```text
query: required search query
limit: default 8
book: optional book id or title
aliases: optional routing aliases
class_codes: optional BMDC class filters
mode: hybrid, vector or fts
include_text: include full chunk text instead of excerpt
```

### `POST /route`

Route a natural language query to likely BMDC classes and aliases.

```bash
curl -X POST http://127.0.0.1:8765/route \
  -H "Content-Type: application/json" \
  -d '{"query": "What do my books say about compound interest?"}'
```

### `GET /chunks/{chunk_id}`

Read a chunk, optionally with symmetric context.

```bash
curl "http://127.0.0.1:8765/chunks/example_chunk_id?context=1"
```

### `GET /chunks/{chunk_id}/around`

Read chunks before and after a known chunk.

```bash
curl "http://127.0.0.1:8765/chunks/example_chunk_id/around?before=2&after=3"
```

### `GET /chunks/{chunk_id}/section`

Read the section containing a chunk.

```bash
curl "http://127.0.0.1:8765/chunks/example_chunk_id/section"
```

### `GET /books/{book_id}/chapters`

List chapters discovered from the indexed chunks for a book.

```bash
curl "http://127.0.0.1:8765/books/scott_adams_how_to_fail/chapters"
```

### `GET /books/{book_id}/chapters/{chapter}`

Read a chapter by chapter ID or title.

```bash
curl "http://127.0.0.1:8765/books/scott_adams_how_to_fail/chapters/Chapter%206"
```

### `POST /topic-map`

Build a topic map across summaries and chunk retrieval.

```bash
curl -X POST http://127.0.0.1:8765/topic-map \
  -H "Content-Type: application/json" \
  -d '{"topic": "systems thinking", "book_limit": 8}'
```

## Container use

For a container, bind to all interfaces:

```bash
bookmem serve --host 0.0.0.0 --port 8765
```

Mount the project or data directories so the API can access:

```text
data/books/
data/lancedb/
data/summaries/
data/manifests/
config/
```

## Recommended client workflow

```text
1. POST /route
2. POST /search using aliases/class_codes from the route
3. GET /chunks/{chunk_id}/around for the strongest result
4. GET /chunks/{chunk_id}/section when more context is needed
5. GET /books/{book_id}/chapters/{chapter} only for wider context
```


## API authentication

Optional bearer-token authentication is available:

```bash
BOOKMEM_API_REQUIRE_KEY=true BOOKMEM_API_KEY=change-me bookmem serve
```

Or:

```bash
bookmem serve --require-api-key --api-key "change-me"
```

Requests must include:

```http
Authorization: Bearer change-me
```

See `docs/API_AUTH.md`.
