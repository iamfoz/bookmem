# Architecture

BookMem is organised around canonical Markdown books and regenerable derived state.

## Pipeline

```text
import
→ raw Markdown
→ clean
→ frontmatter
→ classify
→ prepare
→ ingest
→ summaries/concepts/claims/passages
→ search/answer packs/exports/API/MCP
```

## Canonical and derived state

Canonical:

```text
data/books/
data/raw-books/
config/
```

Derived:

```text
data/summaries/
data/concepts/
data/claims/
data/passages/
data/graphs/
data/notes/
data/lancedb/
exports/
```

The index and exports can be regenerated. Canonical Markdown and reviewed metadata
should be backed up carefully.

## Core modules

```text
clean.py                 Markdown cleaning
frontmatter.py           metadata generation
prepare.py               canonical file preparation
taxonomy.py              BMDC taxonomy support
ingest.py                LanceDB ingestion
search.py                retrieval and reading tools
summaries.py             deterministic summaries
summary_providers.py     summary provider abstraction
concepts.py              reusable model extraction
claims.py                assertion extraction
passages.py              commonplace-book layer
answer_pack.py           structured evidence bundles
book_graph.py            relationship graph
graph_exports.py         graph visualisation exports
profiles.py              environment profiles
permissions.py           agent safety policy
jobs.py                  observability ledger
```

## Agent integrations

Agents can use BookMem through:

```text
CLI JSON output
MCP server
local API
exports
workspace-scoped answer packs
saved query briefs
```

## Operational principles

```text
Keep canonical books readable.
Track provenance.
Prefer deterministic behaviour first.
Mark machine output as machine_draft.
Require human review for trusted knowledge.
Make long-running work observable.
```
