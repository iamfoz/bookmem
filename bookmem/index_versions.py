"""Index/version fingerprinting for BookMem."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
from typing import Any

import lancedb

from . import __version__
from .chunking import CHUNKER_VERSION, INDEX_SCHEMA_VERSION
from .clean import CLEANER_VERSION, DEFAULT_PROFILE_NAME
from .config import get_settings
from .embeddings import embedding_dimension, embedding_model_name, EMBEDDING_PROVIDER
from .manifest import load_manifest, save_manifest


INDEX_VERSIONING_VERSION = "0.1.0"


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def taxonomy_version() -> str | None:
    settings = get_settings()
    path = settings.taxonomy_path
    digest = sha256_file(path)
    if digest:
        return f"sha256:{digest[:16]}"
    return None


def current_index_fingerprint() -> dict[str, Any]:
    settings = get_settings()
    return {
        "index_schema_version": INDEX_SCHEMA_VERSION,
        "chunker_version": CHUNKER_VERSION,
        "embedding_provider": EMBEDDING_PROVIDER,
        "embedding_model": embedding_model_name(),
        "embedding_dimension": embedding_dimension(),
        "cleaner_version": CLEANER_VERSION,
        "cleaning_profile": DEFAULT_PROFILE_NAME,
        "taxonomy_version": taxonomy_version(),
        "bookmem_version": __version__,
        "index_versioning_version": INDEX_VERSIONING_VERSION,
    }


def indexed_table_status() -> dict[str, Any]:
    settings = get_settings()
    if not settings.db_dir.exists():
        return {
            "lancedb_readable": False,
            "table_exists": False,
            "row_count": 0,
            "reason": f"LanceDB directory does not exist: {settings.db_dir}",
        }
    try:
        db = lancedb.connect(str(settings.db_dir))
        table_names = db.table_names()
        if settings.table_name not in table_names:
            return {
                "lancedb_readable": True,
                "table_exists": False,
                "row_count": 0,
                "reason": f"Table not found: {settings.table_name}",
            }
        table = db.open_table(settings.table_name)
        return {
            "lancedb_readable": True,
            "table_exists": True,
            "row_count": table.count_rows(),
            "reason": None,
        }
    except Exception as exc:
        return {
            "lancedb_readable": False,
            "table_exists": False,
            "row_count": 0,
            "reason": str(exc),
        }


def manifest_index_metadata() -> dict[str, Any]:
    manifest = load_manifest()
    metadata = manifest.get("index_metadata")
    if isinstance(metadata, dict):
        return metadata

    # Backwards-compatible fallback: infer from first indexed book record.
    for record in manifest.get("books", []):
        values = {}
        for key in (
            "index_schema_version",
            "chunker_version",
            "embedding_model",
            "embedding_dimension",
            "cleaner_version",
            "taxonomy_version",
        ):
            if record.get(key) is not None:
                values[key] = record.get(key)
        if values:
            return values
    return {}


def compare_fingerprints(stored: dict[str, Any], current: dict[str, Any]) -> list[str]:
    reasons = []
    checks = [
        ("index_schema_version", "index schema version changed"),
        ("chunker_version", "chunker version changed"),
        ("embedding_provider", "embedding provider changed"),
        ("embedding_model", "embedding model changed"),
        ("embedding_dimension", "embedding dimension changed"),
        ("cleaner_version", "cleaner version changed"),
        ("cleaning_profile", "default cleaning profile changed"),
        ("taxonomy_version", "taxonomy version changed"),
    ]

    if not stored:
        return ["index metadata missing from manifest"]

    for key, message in checks:
        stored_value = stored.get(key)
        current_value = current.get(key)
        # If dimension cannot be determined without loading model, do not fail purely on None.
        if key == "embedding_dimension" and current_value is None:
            continue
        if stored_value != current_value:
            reasons.append(f"{message}: stored={stored_value!r}, current={current_value!r}")

    return reasons


def update_manifest_index_metadata(
    *,
    chunk_count: int | None = None,
    book_count: int | None = None,
) -> dict[str, Any]:
    manifest = load_manifest()
    current = current_index_fingerprint()
    table = indexed_table_status()
    metadata = {
        **current,
        "chunk_count": chunk_count if chunk_count is not None else table.get("row_count"),
        "book_count": book_count,
        "lancedb_table": get_settings().table_name,
        "lancedb_dir": str(get_settings().db_dir),
    }
    manifest["index_metadata"] = metadata
    save_manifest(manifest)
    return metadata


def index_status() -> dict[str, Any]:
    current = current_index_fingerprint()
    stored = manifest_index_metadata()
    table = indexed_table_status()
    reasons = compare_fingerprints(stored, current)

    if not table.get("lancedb_readable"):
        reasons.append("LanceDB is not readable")
    elif not table.get("table_exists"):
        reasons.append("LanceDB table is missing")
    elif table.get("row_count", 0) == 0:
        reasons.append("LanceDB table has zero rows")

    stale = bool(reasons)

    return {
        "schema_version": 1,
        "stale": stale,
        "reasons": reasons,
        "stored": stored,
        "current": current,
        "table": table,
    }
