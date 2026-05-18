# Summary Providers

BookMem supports optional summary providers.

The deterministic provider remains the default because it is offline,
repeatable and safe. LLM-assisted providers can produce richer summary maps,
but their output is always marked as a machine draft.

## Configuration

Providers are configured in:

```text
config/summary_providers.yaml
config/summary_providers.d/
```

Default configuration:

```yaml
summary_providers:
  deterministic:
    enabled: true

  openai:
    enabled: false
    model: gpt-5.5-thinking

  local_ollama:
    enabled: false
    model: qwen3
```

## Commands

List providers:

```bash
bookmem summary-providers
```

Validate provider config:

```bash
bookmem validate-summary-providers
```

Deterministic summary:

```bash
bookmem summarise-book "data/books/.../Book.md" --provider deterministic
bookmem summarise-books data/books --provider deterministic
```

OpenAI summary:

```bash
OPENAI_API_KEY=... bookmem summarise-book "data/books/.../Book.md" --provider openai
```

Local Ollama summary:

```bash
bookmem summarise-book "data/books/.../Book.md" --provider local_ollama
bookmem summarise-books data/books --provider local_ollama
```

## Enabling providers

Set `enabled: true` for the provider you want to use.

Example:

```yaml
summary_providers:
  openai:
    enabled: true
    generator: openai
    model: gpt-5.5-thinking
    api_key_env: OPENAI_API_KEY
    temperature: 0.2
    max_input_chars: 120000
```

Ollama example:

```yaml
summary_providers:
  local_ollama:
    enabled: true
    generator: local_ollama
    model: qwen3
    base_url: http://localhost:11434
    temperature: 0.2
    max_input_chars: 120000
```

## Output markers

LLM-assisted summaries always include:

```yaml
generator: openai
provider: openai
model: gpt-5.5-thinking
review_status: machine_draft
summary_kind: llm_assisted
```

Local Ollama output uses:

```yaml
generator: local_ollama
provider: local_ollama
model: qwen3
review_status: machine_draft
summary_kind: llm_assisted
```

Deterministic output uses:

```yaml
generator: deterministic
provider: deterministic
review_status: machine_draft
summary_kind: deterministic_extract
```

## Important rule

Machine-generated summaries are not human-reviewed summaries. They should
remain marked:

```yaml
review_status: machine_draft
```

Change this only after deliberate human review.

## Expected JSON from LLM providers

LLM providers are asked to return strict JSON:

```json
{
  "core_thesis": "one concise paragraph",
  "major_ideas": ["idea 1"],
  "best_for_questions_about": ["topic 1"],
  "keywords": ["keyword 1"],
  "chapters": [
    {
      "title": "Chapter title",
      "summary": "concise chapter summary",
      "major_ideas": ["idea"],
      "headings": ["heading"],
      "keywords": ["keyword"]
    }
  ]
}
```

## Safety and cost

The OpenAI provider sends book text to the configured API provider. Only use
it for books and notes where that is acceptable.

The Ollama provider keeps processing local, assuming your Ollama server is
local and under your control.

## Relationship to deterministic summaries

Deterministic summaries are still useful for:

```text
offline operation
repeatable builds
tests
low-cost indexing
initial corpus bootstrapping
```

LLM-assisted summaries are useful for:

```text
higher-quality core thesis extraction
better chapter summaries
improved routing/search maps
richer Obsidian notes
```
