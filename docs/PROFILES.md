# Config Profiles / Environments

BookMem supports named config profiles for switching between environments
such as local workstation, Docker/container and assistant-agent integrations.

## Profile files

```text
config/profiles/
  local.yaml
  docker.yaml
  assistant_agent.yaml
```

Users can add their own:

```text
config/profiles/server.yaml
config/profiles/my_agent.yaml
```

## Global profile option

Use a profile for any command:

```bash
bookmem --profile assistant_agent search "systems thinking"
bookmem --profile docker serve
bookmem --profile local doctor
```

## Profile commands

Show current profile:

```bash
bookmem profile current
```

List profiles:

```bash
bookmem profile list
```

Show one profile:

```bash
bookmem profile show assistant_agent
```

Persist a profile as current:

```bash
bookmem profile use assistant_agent
```

Validate a profile:

```bash
bookmem profile validate assistant_agent
```

## Environment variable

You can also set:

```bash
export BOOKMEM_PROFILE=assistant_agent
```

`BOOKMEM_PROFILE` takes precedence over the persisted profile file.

## Persisted current profile

`bookmem profile use` writes:

```text
data/manifests/current_profile.yaml
```

## Profile shape

```yaml
schema_version: 1
profile:
  name: assistant_agent
  label: Assistant agent
  description: Generic assistant-agent profile for tool/agent integrations.
  environment: agent

paths:
  data_dir: data
  config_dir: config
  exports_dir: exports
  backups_dir: backups
  lancedb_dir: data/lancedb

services:
  api:
    host: 127.0.0.1
    port: 8765
    require_api_key: true
  mcp:
    enabled: true

retrieval:
  default_workspace:
  default_limit: 8

agent:
  permissions_profile: assistant_agent
  require_confirmation_for_writes: true

features:
  auto_restore_points: true
  audit_log: true
  plugins_enabled: false
```

## Environment overlay

When `--profile` is used, BookMem sets these environment variables for the
command duration:

```text
BOOKMEM_PROFILE
BOOKMEM_DATA_DIR
BOOKMEM_CONFIG_DIR
BOOKMEM_EXPORTS_DIR
BOOKMEM_BACKUPS_DIR
BOOKMEM_LANCEDB_DIR
BOOKMEM_AGENT_PERMISSIONS_PROFILE
```

Current commands can use these immediately. More subsystems can be migrated
over time to respect the profile paths directly.

## Built-in profiles

### `local`

Good for laptop/workstation use.

### `docker`

Container-friendly defaults:

```text
API host: 0.0.0.0
API key required: true
mounted paths under /app/
```

### `assistant_agent`

Generic agent-integration profile:

```text
API key required
MCP enabled
assistant_agent permission profile
lower default retrieval limit
```

## Naming note

The built-in profile is deliberately generic: `assistant_agent`.

If your assistant has a specific local name, create your own profile:

```bash
cp config/profiles/assistant_agent.yaml config/profiles/my_assistant.yaml
```

Then edit the profile name inside the file.

## Validation

```bash
bookmem profile validate docker
```

Validation checks required paths, API port range and basic profile shape.
