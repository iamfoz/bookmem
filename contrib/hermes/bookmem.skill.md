# Skill: Using BookMem from a Hermes agent

This skill tells a Hermes agent how to use BookMem safely and effectively as a
research tool. BookMem turns a private Markdown book corpus into a searchable,
citable retrieval system. Treat it as a read-only research source unless the
user explicitly asks for a corpus-changing operation.

## What BookMem is

BookMem is a command-line tool. From within Hermes it is invoked through the
wrapper installed by `bookmem hermes install-wrapper`:

```
~/.hermes/bin/bookmem <subcommand> [args...]
```

The wrapper sets `BOOKMEM_HOME` and selects the `hermes` profile. The
equivalent direct form, without the wrapper, is:

```
~/.hermes/hermes-agent/venv/bin/bookmem --profile hermes <subcommand> [args...]
```

## Runtime facts

- The BookMem Python package is installed in the Hermes agent virtualenv at
  `~/.hermes/hermes-agent/venv`. There is no separate BookMem virtualenv.
- The BookMem runtime home is `~/.hermes/bookmem`. Books, the index, exports
  and config all live there, not in the virtualenv.
- Do NOT assume `~/code/bookmem` (or any source checkout) is the working
  directory at runtime. It may not exist on the machine, and BookMem does not
  need it. Always invoke BookMem via the wrapper or the venv path above.
- Confirm the integration is healthy with `~/.hermes/bin/bookmem hermes status`.
  This check is passive: it does not load embedding models, initialise LanceDB
  or contact Hugging Face.

## How to answer research questions

1. For a general research question, prefer `answer-pack`. It returns a
   structured, cited answer assembled from the corpus:

   ```
   ~/.hermes/bin/bookmem answer-pack "What do my books say about systems versus goals?" --json
   ```

2. When the relevant scope is already known, use `workspace answer-pack` to
   restrict the search to one workspace. It is tighter and faster than a
   whole-corpus `answer-pack`:

   ```
   ~/.hermes/bin/bookmem workspace answer-pack productivity "systems versus goals" --json
   ```

3. Use `search` to find specific passages, then `read-around` or `read-chapter`
   to pull more surrounding context before quoting.

4. Use `claims compare` to see where books agree or disagree on a topic, and
   `passages search` to look through extracted notable passages.

## Citations are required

BookMem results include citation strings (title, author, chapter or heading
path, line range and chunk ID). When you report a finding to the user, always
surface BookMem's own citation strings. Do not paraphrase a source as if it
were unattributed, and do not invent citations. If a passage has no citation,
say so rather than fabricating one.

## Prefer JSON for machine parsing

When you are parsing BookMem output programmatically, pass `--json` on every
sub-command that supports it (`answer-pack`, `workspace answer-pack`,
`claims compare`, `passages search`, `reading-list`, `jobs status`, `doctor`,
`hermes status`). The human-readable, formatted output is fine to relay
directly to a user, but do not try to scrape structured fields out of it.

## Never run destructive commands without confirmation

The following commands change or rebuild corpus state. Do NOT run them on your
own initiative. Run them only when the user has explicitly asked for that
specific action, and confirm scope first:

- `prepare-books` — rebuilds canonical book structure
- `ingest`, and especially `ingest --reset` — rebuilds the LanceDB index
- `restore` — overwrites runtime data from a backup
- `doctor --fix` — mutates state while repairing (`doctor` without `--fix` is a
  safe, read-only diagnostic)

Anything that prepares, ingests, resets, restores or otherwise writes to the
corpus is out of scope for routine research and needs explicit user
confirmation.

## Respect agent permissions

BookMem ships an agent permissions layer, and the `hermes` profile points at a
permissions profile. Respect it. If a command is denied by permissions, do not
attempt to work around it; report the limitation to the user instead. Stay
within read-oriented research use unless the user directs otherwise.

## Quick reference

```
# health (passive)
~/.hermes/bin/bookmem hermes status --json

# search and read
~/.hermes/bin/bookmem search "compound interest"
~/.hermes/bin/bookmem read-around <chunk_id> --before 2 --after 3
~/.hermes/bin/bookmem read-chapter --book <book_id> --chapter "Chapter 6"

# cited answers
~/.hermes/bin/bookmem answer-pack "<question>" --json
~/.hermes/bin/bookmem workspace answer-pack <workspace> "<question>" --json

# claims, passages, reading lists
~/.hermes/bin/bookmem claims compare "<topic>" --json
~/.hermes/bin/bookmem passages search "<query>" --json
~/.hermes/bin/bookmem reading-list --topic "<topic>" --json

# jobs
~/.hermes/bin/bookmem jobs status <job_id> --json
```
