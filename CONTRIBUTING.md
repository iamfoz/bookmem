# Contributing

Contributions are welcome once the repository is public.

## Development setup

```bash
git clone https://github.com/iamfoz/bookmem.git
cd bookmem

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Checks

Run:

```bash
pytest
ruff check .
bookmem doctor
```

## Documentation

Update documentation in the same change as code. At minimum, update:

```text
README.md
CHANGELOG.md
docs/
```

## Pull requests

Pull requests should be focused, documented and tested. Do not include private books,
indexes, secrets, local `.env` files or generated personal data.
