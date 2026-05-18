# Embedding Model Management

BookMem can manage embedding model profiles explicitly instead of treating
embeddings as a hidden config value.

This matters because changing embedding models can make an existing LanceDB
index stale or incompatible.

## Configuration

Embedding profiles live in:

```text
config/embedding_models.yaml
config/embedding_models.d/
```

Example profile:

```yaml
embedding_models:
  default:
    provider: sentence_transformers
    model: sentence-transformers/all-MiniLM-L6-v2
    dimensions: 384
    normalised: true

  bge-m3:
    provider: sentence_transformers
    model: BAAI/bge-m3
    dimensions: 1024
    normalised: true
```

## Commands

Show current runtime and stored index embedding metadata:

```bash
bookmem embeddings info
bookmem embeddings info --json
```

List configured models:

```bash
bookmem embeddings models
bookmem embeddings models --validate
```

Benchmark a model:

```bash
bookmem embeddings benchmark
bookmem embeddings benchmark --model bge-m3
bookmem embeddings benchmark --model sentence-transformers/all-mpnet-base-v2
```

Reindex with a model:

```bash
bookmem embeddings reindex --model bge-m3
```

Dry run:

```bash
bookmem embeddings reindex --model bge-m3 --dry-run
```

Changed-only mode:

```bash
bookmem embeddings reindex --model bge-m3 --changed-only
```

## Manifest storage

BookMem stores the selected embedding model in the manifest:

```yaml
embedding:
  provider: sentence_transformers
  model: sentence-transformers/all-MiniLM-L6-v2
  dimensions: 384
  normalised: true
  profile: default
  management_version: 0.1.0
```

The index fingerprint also records:

```yaml
embedding_provider: sentence_transformers
embedding_model: sentence-transformers/all-MiniLM-L6-v2
embedding_dimension: 384
embedding_normalised: true
```

## Built-in profiles

```text
default   sentence-transformers/all-MiniLM-L6-v2
bge-small BAAI/bge-small-en-v1.5
bge-base  BAAI/bge-base-en-v1.5
bge-m3    BAAI/bge-m3
mpnet     sentence-transformers/all-mpnet-base-v2
```

## Raw model names

You can pass a raw Sentence Transformers model name:

```bash
bookmem embeddings benchmark --model sentence-transformers/all-mpnet-base-v2
bookmem embeddings reindex --model sentence-transformers/all-mpnet-base-v2
```

## Reindexing guidance

Use a full reset when changing embedding model or dimensions:

```bash
bookmem embeddings reindex --model bge-m3
```

Changed-only reindexing is useful only when the existing table is already
using the same embedding model/dimensions:

```bash
bookmem embeddings reindex --model default --changed-only
```

After changing models, check:

```bash
bookmem index-status
```

## Future direction

The current implementation manages one active embedding model/index at a
time. Later, BookMem can support separate named indexes such as:

```text
fast-local
high-quality
multilingual
cloud
```
