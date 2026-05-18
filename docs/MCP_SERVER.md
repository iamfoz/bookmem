# MCP Server

BookMem includes an optional Model Context Protocol (MCP) server so MCP-capable
agents can search and read the local book corpus directly.

The MCP server is a thin integration layer over the existing BookMem commands.
It does not replace the CLI, the manifest, the Markdown source library, or the
LanceDB index.

## Install

Install BookMem with the normal project dependencies:

```bash
pip install -e .
```

The MCP dependency is declared in `pyproject.toml`:

```text
mcp>=1.2.0
```

## Start the server

The server runs over stdio:

```bash
bookmem serve-mcp
```

Equivalent Python module invocation:

```bash
python -m bookmem.mcp_server
```

## Example MCP client configuration

For a client that accepts JSON MCP server configuration, use the project
virtual environment or absolute paths as appropriate:

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

If the client cannot find the `bookmem` executable, use Python directly:

```json
{
  "mcpServers": {
    "bookmem": {
      "command": "/path/to/bookmem/.venv/bin/python",
      "args": ["-m", "bookmem.mcp_server"],
      "cwd": "/path/to/bookmem"
    }
  }
}
```

## Exposed tools

### `bookmem.search`

Search indexed chunks.

Parameters:

```text
query: str
limit: int = 8
alias: str | None = None
class_code: str | None = None
mode: "hybrid" | "vector" | "fts" = "hybrid"
include_text: bool = False
```

Use this for passage discovery. Prefer `alias` or `class_code` when the
query clearly belongs to a known subject area.

### `bookmem.read_chunk`

Read a chunk and nearby context.

Parameters:

```text
chunk_id: str
context: int = 1
```

### `bookmem.read_around`

Read a configurable number of chunks before and after a chunk.

Parameters:

```text
chunk_id: str
before: int = 2
after: int = 3
```

### `bookmem.read_section`

Read the section containing a chunk.

Parameters:

```text
chunk_id: str
```

### `bookmem.read_chapter`

Read a chapter by book ID/title and chapter ID/title.

Parameters:

```text
book: str
chapter: str
```

### `bookmem.list_books`

List canonical books from Markdown frontmatter.

Parameters:

```text
class_code: str | None = None
author: str | None = None
limit: int = 100
```

### `bookmem.route_query`

Route a natural-language query to likely aliases and BMDC class codes.

Parameters:

```text
query: str
```

### `bookmem.map_topic`

Build a topic map using summaries and chunk retrieval.

Parameters:

```text
topic: str
book_limit: int = 8
summary_limit: int = 20
chunk_limit: int = 20
include_chunks: bool = True
```

## Recommended agent behaviour

Agents should use the MCP tools in this order:

```text
1. bookmem.route_query
2. bookmem.search using the selected alias/class code
3. bookmem.read_around for the strongest result
4. bookmem.read_section if more context is needed
5. bookmem.read_chapter only when chapter-scale context is justified
6. bookmem.map_topic for broad synthesis questions
```

## Citation behaviour

Search and read results include:

```text
source_path
heading_path
chapter_id
section_id
start_line
end_line
citation
chunk_id
```

Agents should include these fields when making claims based on the corpus.

## Requirements before use

The MCP server expects the corpus to have been prepared and indexed:

```bash
bookmem prepare-books data/raw-books --changed-only
bookmem summarise-books data/books
bookmem ingest --changed-only
```

If the schema has changed since the last release, run:

```bash
bookmem ingest --reset
```
