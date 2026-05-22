# Configuration

## Main config

Core configuration lives under:

```text
config/
```

Important files:

```text
config/workspaces.yaml
config/agent_permissions.yaml
config/cleaning_profiles.yaml
config/summary_providers.yaml
config/embedding_models.yaml
config/profiles/
```

## Profiles

Profiles switch environment defaults:

```bash
bookmem profile list
bookmem profile use assistant_agent
bookmem --profile docker serve
```

Built-in profiles:

```text
local
docker
assistant_agent
```

## API authentication

Use a local bearer token when exposing the API beyond localhost:

```bash
BOOKMEM_API_REQUIRE_KEY=true
BOOKMEM_API_KEY="change-me"
bookmem serve --require-api-key
```

## Workspaces

Workspaces limit retrieval scope:

```yaml
workspaces:
  productivity:
    classes: ["158", "650", "658"]
    topics:
      - habits
      - systems
```

## Agent permissions

Agent permissions define allow/confirm/deny rules:

```yaml
agents:
  assistant_agent:
    allow:
      - search
      - read
      - answer_pack
    require_confirmation:
      - prepare_books
      - restore
    deny:
      - delete_canonical_books
```
