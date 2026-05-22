---
name: bookmem
description: >-
  Answer research questions from a private Markdown book corpus with verbatim
  citations, using the BookMem command-line tool.
version: 1.0.0
license: GPL-3.0-only
platforms:
  - linux
  - darwin
metadata:
  hermes:
    config:
      wrapper_path:
        description: >-
          Path to the BookMem wrapper created by `bookmem hermes
          install-wrapper`. The wrapper sets BOOKMEM_HOME and selects the
          BookMem `hermes` profile, so sub-commands need no extra flags.
        default: ~/.hermes/bin/bookmem
---

# BookMem research skill

BookMem turns a private Markdown book corpus into a searchable, citable
research source. Use this skill to answer the user's research questions from
their own books.

BookMem is a command-line tool. Invoke it with the **terminal tool**, running
the configured wrapper path (`wrapper_path`, default `~/.hermes/bin/bookmem`).
The wrapper sets `BOOKMEM_HOME` and selects the `hermes` profile; if it is not
installed, fall back to
`~/.hermes/hermes-agent/venv/bin/bookmem --profile hermes`.

## Answering research questions

For any question about what the books say, run `answer-pack` with `--json`. It
returns a structured, cited evidence bundle:

    ~/.hermes/bin/bookmem answer-pack "<question>" --json

When the relevant workspace is known, scope the query — it is tighter and
faster:

    ~/.hermes/bin/bookmem workspace answer-pack <workspace> "<question>" --json

Use `search` to locate passages, then `read-around` / `read-chapter` to pull
surrounding context before quoting. Use `claims compare` for agreement and
disagreement across books, and `passages search` for extracted passages.

## Cite or say nothing

This is the core rule of this skill:

- **Never present a claim from a book without the citation BookMem returns.**
  Every result carries a citation string (title, author, heading path, line
  range, chunk ID). Surface it verbatim with the claim.
- **Never fabricate or guess a citation.** Use only the citation strings
  BookMem produced.
- **If a result has no citation, say so** — state that the passage is uncited
  rather than inventing attribution.
- If BookMem returns no relevant results, tell the user the corpus does not
  cover the question. Do not fill the gap with general knowledge presented as
  if it came from their books.

## Never mutate the corpus without confirmation

These commands change or rebuild corpus state. Do **not** run them on your own
initiative — only when the user explicitly asks for that specific action, and
confirm the scope first:

- `prepare-books` — rebuilds canonical book structure
- `ingest`, and especially `ingest --reset` — rebuilds the index
- `restore` — overwrites runtime data from a backup
- `doctor --fix` — mutates state while repairing

`doctor` without `--fix`, `search`, `read-*`, `answer-pack`, `claims`,
`passages search`, `reading-list` and `hermes status` are read-only and safe.

## Machine-readable output

Pass `--json` on every sub-command that supports it when parsing output
programmatically: `answer-pack`, `workspace answer-pack`, `claims compare`,
`passages search`, `reading-list`, `jobs status`, `doctor`, `hermes status`.
`search`, `read-around` and `read-chapter` emit human-readable text only.

## Respect agent permissions

BookMem enforces an agent permissions policy via the `hermes` profile. If a
command is denied, report the limitation to the user; do not work around it.

## Quick reference

    ~/.hermes/bin/bookmem hermes status --json
    ~/.hermes/bin/bookmem answer-pack "<question>" --json
    ~/.hermes/bin/bookmem workspace answer-pack <workspace> "<question>" --json
    ~/.hermes/bin/bookmem search "<query>"
    ~/.hermes/bin/bookmem read-around <chunk_id> --before 2 --after 3
    ~/.hermes/bin/bookmem read-chapter --book <book_id> --chapter "<chapter>"
    ~/.hermes/bin/bookmem claims compare "<topic>" --json
    ~/.hermes/bin/bookmem passages search "<query>" --json
    ~/.hermes/bin/bookmem reading-list --topic "<topic>" --json
