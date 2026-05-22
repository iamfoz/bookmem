# Troubleshooting

## `bookmem --help` is slow

This should not happen. The CLI uses lazy imports so help output does not load
embedding dependencies. Check your version:

```bash
bookmem --version
```

Upgrade to the latest local checkout:

```bash
git pull
python -m pip install -e ".[dev]"
```

## `setup status` downloads models

`bookmem setup status` should be passive. Only this command should run index
diagnostics:

```bash
bookmem setup status --include-index
```

## README files are being ingested as books

BookMem excludes support Markdown files such as `README.md`. If this happens,
check that you are using a version with `bookmem/book_files.py`.

```bash
bookmem doctor
```

## Hugging Face rate-limit warning

Set a token if you repeatedly download models:

```bash
export HF_TOKEN="..."
```

Or pre-warm on a machine with internet access.

## LanceDB errors

Run:

```bash
bookmem doctor --deep
bookmem index-status
```

If needed, rebuild:

```bash
bookmem clean-derived --index --dry-run
bookmem clean-derived --index
bookmem ingest --reset
```

## Bad metadata

Run review commands:

```bash
bookmem review
bookmem review classifications
bookmem review isbn-conflicts
```

## Broken citations

Run:

```bash
bookmem doctor --deep
```

Deep doctor samples citations and checks that line ranges point to valid files.
