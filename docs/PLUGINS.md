# Plugins

BookMem supports lightweight plugin discovery through YAML manifests.

This first version is intentionally conservative:

```text
discover manifests
validate metadata
validate optional entrypoint references
do not execute plugin code
```

## Directories

```text
plugins/
  importers/
  enrichers/
  exporters/
  summary_providers/
  citation_styles/
```

## Commands

List plugins:

```bash
bookmem plugins list
```

Filter by category:

```bash
bookmem plugins list --category importers
bookmem plugins list --category summary_providers
```

Show enabled plugins only:

```bash
bookmem plugins list --enabled-only
```

JSON:

```bash
bookmem plugins list --json
```

Validate manifests:

```bash
bookmem plugins validate
bookmem plugins validate --json
```

## Manifest shape

A plugin manifest can be a direct YAML file inside a category directory:

```text
plugins/importers/my_importer.yaml
```

Or:

```text
plugins/importers/my_importer/plugin.yaml
```

Example:

```yaml
schema_version: 1
plugin:
  id: calibre_extra_importer
  name: Calibre Extra Importer
  category: importers
  version: 0.1.0
  description: Imports additional Calibre-derived formats.
  enabled: false

  entrypoint:
    module: my_bookmem_plugins.calibre_extra
    object: import_book

  capabilities:
    - import.calibre
    - import.metadata

  config_schema:
    type: object
    properties:
      preserve_covers:
        type: boolean
```

## Categories

```text
importers
enrichers
exporters
summary_providers
citation_styles
```

## Entrypoints

Entrypoints are metadata only in this initial implementation.

BookMem validates whether the module is importable in the current environment,
but it does not execute plugin code.

This keeps plugin discovery safe while still giving the project a clean path
towards future runtime plugin loading.

## Capabilities

Capabilities should describe what the plugin offers:

```text
import.epub
import.pdf
enrich.metadata
export.graph
summarise.book
citation.format
```

## Validation

Validation checks:

```text
manifest can be loaded
plugin mapping exists
plugin id is unique
category is recognised
capabilities are present
enabled plugins have useful entrypoint metadata
entrypoint module is importable where declared
```

## Safety

The plugin architecture should not become a back door for arbitrary execution.

Recommended policy:

```text
manifests are safe to read
plugin execution should require explicit enablement
agent permissions should control plugin-backed actions
plugin actions should write audit records
destructive plugin actions should create restore points
```

## Future runtime loading

A later version can map plugin capabilities into BookMem command registries,
for example:

```text
importers       -> bookmem import ...
enrichers       -> bookmem enrich-metadata ...
exporters       -> bookmem export ...
summary providers -> bookmem summarise-book --provider ...
citation styles -> bookmem citations ...
```

For now, plugin discovery gives the project a clean extension point without
turning the codebase into a monolith.
