# BookMem contrib: Hermes integration

This directory holds assets for running BookMem as a tool for a Hermes agent.
None of these files are required to use BookMem standalone; they exist to make
the Hermes integration quick to install and safe for an agent to use.

## How BookMem runs under Hermes

- The BookMem Python package is installed INTO the Hermes agent virtualenv at
  `~/.hermes/hermes-agent/venv`. No separate BookMem virtualenv is created.
- The BookMem runtime home is `~/.hermes/bookmem`. Config, data (books, the
  LanceDB index, manifests, summaries, passages, jobs, audit and more),
  exports, backups and logs all live there, never inside the virtualenv.
- A small wrapper at `~/.hermes/bin/bookmem` sets `BOOKMEM_HOME` and runs
  BookMem with the `hermes` profile, so the agent can call BookMem without
  caring where the package or the data lives.

The runtime root is resolved by BookMem in this precedence order: the `--home`
option, the `BOOKMEM_HOME` environment variable, the selected profile's
`paths.home_dir`, Hermes auto-detection (the interpreter running inside the
Hermes venv), and finally the current working directory as a standalone
fallback.

## Files in this directory

- `install.sh` — Bash installer. Installs the BookMem package into the Hermes
  agent venv, creates the runtime home, and installs the wrapper. Safe to
  re-run.
- `bookmem.tool.yaml` — Hermes tool manifest. Describes the BookMem tool and
  the sub-commands an agent may invoke (`search`, `answer-pack`, `read-around`,
  `read-chapter`, `workspace answer-pack`, `claims compare`, `passages search`,
  `reading-list`, `jobs status`, `doctor`, `hermes status`).
- `bookmem.skill.md` — Skill document. Tells a Hermes agent how to use BookMem
  safely: prefer cited answer packs, always cite sources, prefer `--json` for
  machine parsing, and never run destructive commands without explicit user
  confirmation.
- `README.md` — This file.

## Install

### Option A: scripted install (recommended)

1. Clone the BookMem repository (the default location the script expects is
   `~/code/bookmem`):

   ```bash
   git clone https://github.com/iamfoz/bookmem.git ~/code/bookmem
   ```

2. Run the installer. With no argument it uses `~/code/bookmem`; pass a path to
   use a checkout elsewhere:

   ```bash
   ~/code/bookmem/contrib/hermes/install.sh
   # or, for a checkout in another location:
   ~/code/bookmem/contrib/hermes/install.sh /path/to/bookmem
   ```

The script verifies the Hermes agent venv exists at
`~/.hermes/hermes-agent/venv`, installs BookMem into it, then runs
`bookmem hermes init` and `bookmem hermes install-wrapper`.

### Option B: manual install

1. Clone the repository:

   ```bash
   git clone https://github.com/iamfoz/bookmem.git ~/code/bookmem
   cd ~/code/bookmem
   ```

2. Install the BookMem package into the Hermes agent venv. This is the
   canonical install command:

   ```bash
   $HOME/.hermes/hermes-agent/venv/bin/python -m pip install -U .
   ```

   For an editable development install, add `-e`:

   ```bash
   $HOME/.hermes/hermes-agent/venv/bin/python -m pip install -U -e .
   ```

3. Create the runtime home and install the wrapper:

   ```bash
   $HOME/.hermes/hermes-agent/venv/bin/bookmem hermes init
   $HOME/.hermes/hermes-agent/venv/bin/bookmem hermes install-wrapper
   ```

   You can print these commands at any time with:

   ```bash
   $HOME/.hermes/hermes-agent/venv/bin/bookmem hermes install-help
   ```

## The `bookmem hermes` commands

All four support `--json`; `init` and `install-wrapper` also support
`--dry-run` and `--force`.

- `bookmem hermes init` — creates `~/.hermes/bookmem` and its subdirectories
  and copies the default config.
- `bookmem hermes status` — passive health check of the integration. It does
  not load embedding models, initialise LanceDB or contact Hugging Face.
- `bookmem hermes install-wrapper` — creates the `~/.hermes/bin/bookmem`
  wrapper.
- `bookmem hermes install-help` — prints the canonical install commands.

## Verify

After installing, confirm the integration is healthy:

```bash
~/.hermes/bin/bookmem hermes status
```

Make sure `~/.hermes/bin` is on the agent's PATH. The agent can then call
BookMem through the wrapper, for example:

```bash
~/.hermes/bin/bookmem search "systems versus goals"
~/.hermes/bin/bookmem answer-pack "What do my books say about goals?" --json
```

Register `bookmem.tool.yaml` with your Hermes setup as the tool manifest, and
provide `bookmem.skill.md` as the usage skill so the agent uses BookMem safely.
