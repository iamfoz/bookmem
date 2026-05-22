# Quick Start

This guide gets BookMem from zero to searchable corpus.

## 1. Install

```bash
git clone https://github.com/iamfoz/bookmem.git
cd bookmem

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## 2. Check the installation

```bash
bookmem --help
bookmem doctor
bookmem setup presets
bookmem setup status
```

## 3. Add books

Put Markdown books in:

```text
data/raw-books/
```

Recommended filename:

```text
<Title> - <Author> - <ISBN>.md
```

Example:

```text
Atomic Habits - James Clear - 9780735211292.md
```

## 4. Prepare books

```bash
bookmem prepare-books data/raw-books --changed-only
```

Canonical books are written under:

```text
data/books/
```

## 5. Ingest

```bash
bookmem ingest --changed-only
```

## 6. Search

```bash
bookmem search "systems versus goals"
```

## 7. Generate an answer pack

```bash
bookmem answer-pack "What do my books say about systems versus goals?" --json
```

## 8. Use a workspace

```bash
bookmem workspace list
bookmem workspace answer-pack productivity "systems versus goals"
```

## 9. Create a brief

```bash
bookmem query save "systems versus goals" --name systems-goals --workspace productivity
bookmem brief generate systems-goals
```

## 10. Maintain the corpus

```bash
bookmem doctor
bookmem doctor --deep
bookmem backup --output backups/bookmem-$(date +%Y-%m-%d).tar.gz
```
