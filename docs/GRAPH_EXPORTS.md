# Graph Visualisation Exports

BookMem can export the derived book graph into visualisation-friendly formats.

Source graph:

```text
data/graphs/book_graph.json
```

Export directory:

```text
exports/graphs/
```

## Commands

List formats:

```bash
bookmem graph formats
```

Export GraphML:

```bash
bookmem graph export --format graphml
```

Output:

```text
exports/graphs/book_graph.graphml
```

Export Cytoscape JSON:

```bash
bookmem graph export --format cytoscape
```

Output:

```text
exports/graphs/book_graph.cyjs
```

Export Mermaid:

```bash
bookmem graph export --format mermaid
```

Output:

```text
exports/graphs/book_graph.mmd
```

Export Obsidian Canvas:

```bash
bookmem graph export --format obsidian-canvas
```

Output:

```text
exports/graphs/book_graph.canvas
```

Export all formats:

```bash
bookmem graph export --format all
```

Rebuild graph before exporting:

```bash
bookmem graph export --format all --rebuild
```

Custom output:

```bash
bookmem graph export --format graphml --output exports/graphs/my_graph.graphml
```

JSON output:

```bash
bookmem graph export --format obsidian-canvas --json
```

Limit Mermaid edges for readability:

```bash
bookmem graph export --format mermaid --max-edges 100
```

## Supported formats

### GraphML

Useful for:

```text
Gephi
yEd
Cytoscape import workflows
NetworkX
graph analytics tools
```

### Cytoscape JSON

Useful for:

```text
Cytoscape.js
web visualisations
graph dashboards
```

### Mermaid

Useful for:

```text
Markdown previews
GitHub docs
quick diagrams
lightweight graph snapshots
```

For large libraries, use `--max-edges`.

### Obsidian Canvas

Useful for:

```text
human browsing
note workflows
visual book maps
workspace/project thinking
```

The Canvas export uses file nodes where possible, pointing back to canonical
Markdown books.

## Audit

Graph export writes audit records:

```text
graph.export
```

## Recommended workflow

```bash
bookmem build-graph
bookmem graph export --format obsidian-canvas
bookmem graph export --format graphml
```

Or:

```bash
bookmem graph export --format all --rebuild
```
