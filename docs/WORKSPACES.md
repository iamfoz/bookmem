# Workspaces

Workspaces are named corpus scopes.

They let an agent or human ask a question against a relevant subset of the
library instead of searching every book.

## Configuration

Workspaces live in:

```text
config/workspaces.yaml
```

Example:

```yaml
workspaces:
  productivity:
    classes: ["158", "650"]
    topics:
      - habits
      - systems
      - personal effectiveness

  finance:
    classes: ["330", "332", "336"]
    topics:
      - investing
      - valuation
      - risk
```

## Commands

List workspaces:

```bash
bookmem workspace list
```

Validate config:

```bash
bookmem workspace validate
```

Search a workspace:

```bash
bookmem workspace search productivity "systems versus goals"
bookmem workspace search finance "risk and return"
```

JSON search:

```bash
bookmem workspace search productivity "systems versus goals" --json
```

Build a scoped answer pack:

```bash
bookmem workspace answer-pack finance "risk and return"
bookmem workspace answer-pack productivity "systems versus goals" --json
```

## Built-in workspaces

```text
productivity
finance
agent_infrastructure
```

## How search is scoped

Workspace search uses:

```text
classes
aliases
topics
```

Search order:

```text
1. BMDC class filters
2. routing aliases
3. topic-enriched fallback search
```

## Why this matters for agents

Without workspaces, an agent has to infer scope every time.

With workspaces, the caller can say:

```bash
bookmem workspace answer-pack finance "compound interest"
```

That reduces ambiguity and helps prevent irrelevant books from dominating
retrieval.

## Workspace answer packs

Workspace answer packs include the normal answer-pack structure plus:

```json
{
  "workspace": {},
  "workspace_query": "...",
  "workspace_results": []
}
```

Agents should prefer workspace results before broad-corpus evidence.

## Custom workspaces

Add your own:

```yaml
workspaces:
  leadership:
    label: Leadership and management
    description: Leadership, teams, communication and management.
    classes: ["658", "650"]
    topics:
      - leadership
      - teams
      - management
    aliases:
      - leadership
      - management
```
