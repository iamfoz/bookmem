# Prompt Packs

BookMem includes reusable prompt assets under:

```text
prompts/
```

Prompts are first-class project artefacts rather than hidden strings buried
in Python code.

## Included prompts

```text
prompts/summarise_book.md
prompts/generate_implementation_notes.md
prompts/classify_book.md
prompts/extract_key_models.md
prompts/answer_from_corpus.md
```

## Commands

List prompts:

```bash
bookmem prompts list
```

JSON output:

```bash
bookmem prompts list --json
```

Show a prompt:

```bash
bookmem prompts show summarise_book
bookmem prompts show generate_implementation_notes
bookmem prompts show classify_book
bookmem prompts show extract_key_models
bookmem prompts show answer_from_corpus
```

## Why prompts are files

Prompt files are easier to:

```text
review
version
diff
edit
test
share between agents
reuse from an assistant agent/OpenClaw/Claude Code
```

## Recommended use

Agents should treat these prompts as reusable policy and task assets.

Example:

```text
1. Use `bookmem prompts show answer_from_corpus`.
2. Use `bookmem answer-pack "<question>" --json`.
3. Combine the prompt and answer pack in the downstream model.
4. Produce a cited answer.
```

## Custom prompts

Add new Markdown files under `prompts/`.

File name becomes the prompt name:

```text
prompts/my_custom_prompt.md
```

Command:

```bash
bookmem prompts show my_custom_prompt
```

## Prompt design rule

Prompts should describe the task, input expectations, output format and
guardrails. They should not silently alter canonical metadata or claim
machine output is human-reviewed.
