# Terminal UI

BookMem includes a Textual-based terminal UI for managing the corpus without
needing to remember every CLI command.

The TUI is designed around terminal-first UX principles:

```text
persistent spatial layout
keyboard-first navigation
progressive help
semantic status colours
safe allowlisted control actions
readable long-task output
responsive terminal panes
```

The LobeHub TUI design guidance emphasises spatial consistency, keyboard
fluency, a discoverable footer, responsive layouts, semantic colour slots,
focus management and safe confirmations for serious actions. BookMem's TUI
follows those principles by keeping major views fixed, exposing essential
shortcuts in the footer, using tabs/panels rather than hidden flows, and
limiting control-panel execution to known safe commands.

## Run

```bash
bookmem tui
```

## Views

```text
Dashboard
Books
Search
Review
Duplicates
System
Control
```

## Dashboard

Shows high-level state:

```text
book count
indexed chunks
review item count
index status
doctor output
index-status output
```

## Books

Browse and filter canonical books.

Filtering is live in the books tab.

## Search

Run corpus search from inside the TUI. Search output includes route
information, top results and citations.

## Review

Displays review queue files:

```text
needs_metadata.yaml
needs_classification.yaml
low_confidence_matches.yaml
possible_duplicates.yaml
```

## Duplicates

Shows duplicate groups from the duplicate detector.

## System

Shows full diagnostic JSON from:

```text
bookmem doctor
bookmem index-status
```

## Control panel

The control panel can run only allowlisted commands:

```text
bookmem doctor
bookmem doctor --fix
bookmem index-status
bookmem build-graph
bookmem eval retrieval
bookmem ingest --changed-only
bookmem prepare-books data/raw-books --changed-only
```

It streams output into a log panel, which makes it more useful for long
operations like ingestion.

## Keybindings

```text
q       quit
r       refresh
/       focus search/filter
?       toggle help footer
Tab     change focus
Enter   select/submit
```

## Design notes

The TUI deliberately uses a persistent layout rather than a wizard-only menu.
Users build spatial memory: books, search, review, system status and control
stay in fixed tabs.

A setup wizard can be added later as a focused view inside this same TUI,
rather than a separate tool.

## Terminal size

A minimum terminal size of roughly 100x30 is recommended. Textual will handle
resize events, but smaller terminals will be cramped.
