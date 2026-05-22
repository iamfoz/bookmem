# Installation

## Requirements

BookMem requires:

```text
Python 3.11 or newer
Git
pip, pipx or a virtual environment
```

Optional but recommended:

```text
Docker
GitHub CLI
Hermes or another MCP-capable agent
```

## Local development install

```bash
git clone https://github.com/iamfoz/bookmem.git
cd bookmem

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Check:

```bash
bookmem --help
pytest
ruff check .
```

## pipx install from local checkout

```bash
pipx install --editable .
bookmem --help
```

## Docker

```bash
docker compose up --build bookmem-api
```

Run commands inside the container:

```bash
docker compose run --rm bookmem-api bookmem doctor
```

## Hermes install

In Hermes mode the BookMem package is installed into the existing Hermes agent
virtualenv (`~/.hermes/hermes-agent/venv`). There is no separate BookMem
virtualenv. Runtime data and config live separately under `~/.hermes/bookmem`.

Clone the repo, then install the package into the Hermes venv:

```bash
git clone https://github.com/iamfoz/bookmem.git ~/code/bookmem
cd ~/code/bookmem

$HOME/.hermes/hermes-agent/venv/bin/python -m pip install -U .
```

For an editable development install:

```bash
$HOME/.hermes/hermes-agent/venv/bin/python -m pip install -U -e .
```

Initialise the runtime home and optionally install the wrapper:

```bash
$HOME/.hermes/hermes-agent/venv/bin/bookmem hermes init
$HOME/.hermes/hermes-agent/venv/bin/bookmem hermes install-wrapper
```

See [Hermes integration](HERMES.md) for the full setup.

## First run

```bash
bookmem setup presets
bookmem setup run --preset balanced
bookmem setup status
```

`setup status` is passive by default. Use this only when you want embedding/index checks:

```bash
bookmem setup status --include-index
```

## Updating

```bash
git pull
python -m pip install -e ".[dev]"
bookmem migrations status
bookmem migrations apply
bookmem doctor --deep
```
