# Web UI

BookMem includes a small local web UI.

It is deliberately lightweight: no Node build step, no frontend framework,
and no separate database. It sits on top of the existing BookMem Python
modules and generated files.

## Run

```bash
bookmem ui
```

Custom host/port:

```bash
bookmem ui --host 0.0.0.0 --port 8787
```

Open:

```text
http://127.0.0.1:8787
```

## Docker

```bash
docker compose up -d bookmem-ui
```

Open:

```text
http://localhost:8787
```

## Views

The UI includes:

```text
Dashboard
Books
Classes
Review queue
Duplicates
Search
Topic maps
Clean-check reports
System status
Control panel
```

## Dashboard

Shows:

```text
book count
indexed chunk count
review item count
unclassified count
doctor status
index status
```

## Books

Lists books from `data/books/` with:

```text
title
author
BMDC class
class label
topics
source path
```

Supports title/author/topic search and class filtering.

## Classes

Shows class counts based on canonical book frontmatter.

## Search

Runs corpus search and displays:

```text
route
matching books
heading/location
citation
excerpt
```

## Topic maps

Runs topic-map generation from the UI.

## Review queue

Displays review queue YAML files such as:

```text
needs_metadata.yaml
needs_classification.yaml
low_confidence_matches.yaml
possible_duplicates.yaml
```

## Duplicates

Displays duplicate groups using the existing duplicate detector.

## Clean-check reports

Lets you run a clean-check against a Markdown file path and view the summary
and recommendations.

## System status

Displays full JSON output from:

```text
bookmem doctor
bookmem index-status
```

## Control panel

The control panel can run only allowlisted safe commands:

```text
bookmem doctor
bookmem doctor --fix
bookmem index-status
bookmem build-graph
bookmem eval retrieval
```

It does not expose arbitrary shell execution.

## Security

The web UI is intended for local/trusted-network use.

Do not expose it directly to the public internet. If you need remote access,
place it behind your existing reverse proxy and authentication layer.
