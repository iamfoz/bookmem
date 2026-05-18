# Local API Authentication

BookMem supports optional bearer-token authentication for the local FastAPI
service.

This is intentionally simple. It is designed for localhost, trusted Docker
networks and internal agent infrastructure. It is not OAuth and does not try
to be a full identity provider.

## Enable with CLI flags

```bash
bookmem serve --require-api-key --api-key "change-me"
```

Then call the API with:

```bash
curl -H "Authorization: Bearer change-me" http://127.0.0.1:8765/books
```

## Enable with environment variables

```bash
export BOOKMEM_API_REQUIRE_KEY=true
export BOOKMEM_API_KEY="change-me"
bookmem serve
```

## Docker Compose

Create a local `.env` file beside `docker-compose.yml`:

```env
BOOKMEM_API_REQUIRE_KEY=true
BOOKMEM_API_KEY=change-me
```

Then run:

```bash
docker compose up -d bookmem-api
```

Request example:

```bash
curl -H "Authorization: Bearer change-me" http://localhost:8765/books
```

## Health endpoint

`GET /health` remains public so Docker and reverse proxies can perform simple
health checks. It returns whether API auth is currently required:

```json
{
  "status": "ok",
  "version": "0.26.0",
  "api_auth_required": "true"
}
```

## Protected endpoints

When authentication is enabled, the following endpoints require a bearer
token:

```text
GET  /books
POST /search
POST /route
GET  /chunks/{chunk_id}
GET  /chunks/{chunk_id}/around
GET  /chunks/{chunk_id}/section
GET  /books/{book_id}/chapters
GET  /books/{book_id}/chapters/{chapter}
POST /topic-map
```

## Failure behaviour

Missing token:

```text
401 Missing bearer token.
```

Wrong token:

```text
403 Invalid bearer token.
```

Auth required but no key configured:

```text
500 BOOKMEM_API_REQUIRE_KEY is enabled but BOOKMEM_API_KEY is not set.
```

## Security notes

Keep this boring and local:

```text
use a long random token
do not commit real tokens
prefer environment variables over command-line flags
place the API behind your existing reverse proxy/auth layer if exposed wider
```

For public internet exposure, use a proper reverse proxy and authentication
layer rather than relying only on this local bearer token.
