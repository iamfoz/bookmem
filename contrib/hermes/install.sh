#!/usr/bin/env bash
#
# install.sh - Install BookMem into the Hermes agent and wire up the wrapper.
#
# This script installs the BookMem Python package INTO the Hermes agent
# virtualenv (~/.hermes/hermes-agent/venv). It does NOT create a separate
# BookMem virtualenv, and it does NOT place runtime data inside the venv.
# Runtime data and config live under ~/.hermes/bookmem.
#
# Usage:
#   ./install.sh [REPO_PATH]
#
#   REPO_PATH  Path to a BookMem source checkout. Defaults to $HOME/code/bookmem.
#
# The script is safe to re-run: pip upgrades in place, and `bookmem hermes
# init` / `install-wrapper` leave existing files untouched unless forced.

set -euo pipefail

# --- Configuration ----------------------------------------------------------

REPO_PATH="${1:-$HOME/code/bookmem}"
HERMES_VENV="$HOME/.hermes/hermes-agent/venv"
VENV_PYTHON="$HERMES_VENV/bin/python"
VENV_BOOKMEM="$HERMES_VENV/bin/bookmem"

# --- Helpers ----------------------------------------------------------------

info() { printf '==> %s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# Run a BookMem subcommand through the Hermes venv. Prefer the console script;
# fall back to `python -m bookmem.cli` if the console script is not present.
run_bookmem() {
  if [ -x "$VENV_BOOKMEM" ]; then
    "$VENV_BOOKMEM" "$@"
  else
    "$VENV_PYTHON" -m bookmem.cli "$@"
  fi
}

# --- Preflight checks -------------------------------------------------------

info "BookMem Hermes installer"
info "Repository path:    $REPO_PATH"
info "Hermes agent venv:  $HERMES_VENV"

if [ ! -d "$REPO_PATH" ]; then
  fail "BookMem repository not found at: $REPO_PATH
       Clone it first, for example:
         git clone https://github.com/iamfoz/bookmem.git \"$REPO_PATH\"
       or pass the checkout path as the first argument:
         ./install.sh /path/to/bookmem"
fi

if [ ! -f "$REPO_PATH/pyproject.toml" ]; then
  fail "No pyproject.toml in $REPO_PATH; that does not look like a BookMem checkout."
fi

if [ ! -d "$HERMES_VENV" ]; then
  fail "Hermes agent virtualenv not found at: $HERMES_VENV
       Install or repair the Hermes agent before running this script.
       BookMem installs into the existing Hermes venv and does not create
       its own virtualenv."
fi

if [ ! -x "$VENV_PYTHON" ]; then
  fail "No Python interpreter at: $VENV_PYTHON
       The Hermes agent virtualenv looks incomplete."
fi

# --- Step 1: install the BookMem package into the Hermes venv ---------------

info "Installing BookMem into the Hermes agent venv (pip install -U .)"
(
  cd "$REPO_PATH"
  "$VENV_PYTHON" -m pip install -U .
)
info "BookMem package installed."

# --- Step 2: create the Hermes runtime home ---------------------------------

info "Creating the Hermes runtime home (~/.hermes/bookmem) and seeding config"
run_bookmem hermes init
info "Runtime home ready."

# --- Step 3: install the wrapper --------------------------------------------

info "Installing the wrapper at ~/.hermes/bin/bookmem"
run_bookmem hermes install-wrapper
info "Wrapper installed."

# --- Step 4: install the BookMem research skill -----------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SRC="${SCRIPT_DIR}/SKILL.md"
SKILL_DEST_DIR="${HOME}/.hermes/skills/research/bookmem"

if [ -f "${SKILL_SRC}" ]; then
  info "Installing the BookMem research skill to ${SKILL_DEST_DIR}"
  mkdir -p "${SKILL_DEST_DIR}"
  cp "${SKILL_SRC}" "${SKILL_DEST_DIR}/SKILL.md"
  info "Skill installed."
else
  warn "Skill source not found at ${SKILL_SRC}; skipping skill installation."
fi

# --- Done -------------------------------------------------------------------

info "Done."
cat <<'EOF'

BookMem is installed for Hermes.

  Runtime home:  ~/.hermes/bookmem
  Wrapper:       ~/.hermes/bin/bookmem
  Package:       installed in ~/.hermes/hermes-agent/venv
  Skill:         ~/.hermes/skills/research/bookmem/SKILL.md

Verify the integration (passive, no embeddings or LanceDB init):

  ~/.hermes/bin/bookmem hermes status

Ensure ~/.hermes/bin is on the agent's PATH, then call BookMem as:

  ~/.hermes/bin/bookmem search "your query"
  ~/.hermes/bin/bookmem answer-pack "your question" --json

EOF
