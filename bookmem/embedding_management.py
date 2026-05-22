"""Embedding model management for BookMem."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import os
import statistics
import time
from typing import Any

import yaml

from .embeddings import embed_texts, embedding_dimension, embedding_model_name, EMBEDDING_PROVIDER
from .index_versions import current_index_fingerprint, update_manifest_index_metadata
from .manifest import load_manifest, save_manifest


EMBEDDING_MANAGEMENT_VERSION = "0.1.0"


@dataclass
class EmbeddingProfile:
    name: str
    label: str
    provider: str
    model: str
    dimensions: int | None
    normalised: bool
    notes: str | None = None


def load_embedding_models() -> dict[str, dict[str, Any]]:
    models: dict[str, dict[str, Any]] = {}
    base = Path("config/embedding_models.yaml")
    if base.exists():
        data = yaml.safe_load(base.read_text(encoding="utf-8")) or {}
        models.update(data.get("embedding_models", {}))

    custom_dir = Path("config/embedding_models.d")
    if custom_dir.exists():
        for path in sorted(custom_dir.glob("*.y*ml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            models.update(data.get("embedding_models", {}))

    if "default" not in models:
        models["default"] = {
            "label": "Fast local default",
            "provider": "sentence_transformers",
            "model": "sentence-transformers/all-MiniLM-L6-v2",
            "dimensions": 384,
            "normalised": True,
        }
    return models


def validate_embedding_models() -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for name, cfg in load_embedding_models().items():
        if not isinstance(cfg, dict):
            issues.append({"model": name, "issue": "invalid_profile", "message": "Profile must be a mapping."})
            continue
        if not cfg.get("provider"):
            issues.append({"model": name, "issue": "missing_provider", "message": "provider is required."})
        if not cfg.get("model"):
            issues.append({"model": name, "issue": "missing_model", "message": "model is required."})
        if cfg.get("provider") != "sentence_transformers":
            issues.append({"model": name, "issue": "unsupported_provider", "message": "Only sentence_transformers is supported currently."})
        if cfg.get("dimensions") is not None and not isinstance(cfg.get("dimensions"), int):
            issues.append({"model": name, "issue": "invalid_dimensions", "message": "dimensions must be an integer."})
        if cfg.get("normalised") is not None and not isinstance(cfg.get("normalised"), bool):
            issues.append({"model": name, "issue": "invalid_normalised", "message": "normalised must be true or false."})
    return issues


def embedding_profiles() -> list[EmbeddingProfile]:
    profiles = []
    for name, cfg in sorted(load_embedding_models().items()):
        profiles.append(
            EmbeddingProfile(
                name=name,
                label=str(cfg.get("label") or name),
                provider=str(cfg.get("provider") or ""),
                model=str(cfg.get("model") or ""),
                dimensions=cfg.get("dimensions"),
                normalised=bool(cfg.get("normalised", True)),
                notes=cfg.get("notes"),
            )
        )
    return profiles


def resolve_embedding_profile(name_or_model: str | None = None) -> EmbeddingProfile:
    models = load_embedding_models()
    name_or_model = name_or_model or "default"
    if name_or_model in models:
        cfg = models[name_or_model]
        return EmbeddingProfile(
            name=name_or_model,
            label=str(cfg.get("label") or name_or_model),
            provider=str(cfg.get("provider") or "sentence_transformers"),
            model=str(cfg.get("model")),
            dimensions=cfg.get("dimensions"),
            normalised=bool(cfg.get("normalised", True)),
            notes=cfg.get("notes"),
        )

    # Treat unknown value as a raw sentence-transformers model name.
    return EmbeddingProfile(
        name=name_or_model,
        label=name_or_model,
        provider="sentence_transformers",
        model=name_or_model,
        dimensions=None,
        normalised=True,
        notes="Raw model name supplied directly.",
    )


def current_embedding_info() -> dict[str, Any]:
    manifest = load_manifest()
    stored = manifest.get("index_metadata", {}) if isinstance(manifest.get("index_metadata"), dict) else {}
    return {
        "current_runtime": {
            "provider": EMBEDDING_PROVIDER,
            "model": embedding_model_name(),
            "dimensions": embedding_dimension(),
            "normalised": True,
        },
        "stored_index": {
            "provider": stored.get("embedding_provider"),
            "model": stored.get("embedding_model"),
            "dimensions": stored.get("embedding_dimension"),
            "normalised": stored.get("embedding_normalised", stored.get("normalised")),
        },
        "manifest_embedding": manifest.get("embedding"),
        "index_fingerprint": current_index_fingerprint(),
    }


def set_embedding_env(profile: EmbeddingProfile) -> None:
    # BookMem settings read BOOKMEM_EMBEDDING_MODEL through config.
    os.environ["BOOKMEM_EMBEDDING_MODEL"] = profile.model


def update_manifest_embedding(profile: EmbeddingProfile) -> dict[str, Any]:
    manifest = load_manifest()
    manifest["embedding"] = {
        "provider": profile.provider,
        "model": profile.model,
        "dimensions": profile.dimensions,
        "normalised": profile.normalised,
        "profile": profile.name,
        "management_version": EMBEDDING_MANAGEMENT_VERSION,
    }
    save_manifest(manifest)
    return manifest["embedding"]


def benchmark_embeddings(
    profile_name: str | None = None,
    sample_texts: list[str] | None = None,
    runs: int = 3,
) -> dict[str, Any]:
    profile = resolve_embedding_profile(profile_name)
    set_embedding_env(profile)

    sample_texts = sample_texts or [
        "Systems thinking helps explain how feedback loops shape long-term outcomes.",
        "Compound interest is the process by which returns generate further returns.",
        "Personal productivity often depends on habits, environment and attention.",
        "A good evidence pack should include citations and surrounding context.",
        "Finance books often distinguish cash flow, risk, valuation and incentives.",
    ]

    timings = []
    dimensions = None
    vector_count = 0
    for _ in range(max(1, runs)):
        start = time.perf_counter()
        vectors = embed_texts(sample_texts)
        elapsed = time.perf_counter() - start
        timings.append(elapsed)
        vector_count = len(vectors)
        if vectors:
            dimensions = len(vectors[0])

    return {
        "profile": asdict(profile),
        "runs": runs,
        "texts": len(sample_texts),
        "vectors": vector_count,
        "dimensions": dimensions,
        "seconds_min": round(min(timings), 4),
        "seconds_mean": round(statistics.mean(timings), 4),
        "seconds_max": round(max(timings), 4),
        "texts_per_second_mean": round((len(sample_texts) / statistics.mean(timings)), 3) if statistics.mean(timings) else None,
    }


def reindex_with_embedding_model(
    profile_name: str,
    reset: bool = True,
    changed_only: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    profile = resolve_embedding_profile(profile_name)
    if dry_run:
        return {
            "dry_run": True,
            "profile": asdict(profile),
            "would_set_env": {"BOOKMEM_EMBEDDING_MODEL": profile.model},
            "would_run": "bookmem ingest --reset" if reset else "bookmem ingest --changed-only",
        }

    set_embedding_env(profile)
    update_manifest_embedding(profile)

    from .ingest import ingest_books

    ingest_books(reset=reset, changed_only=changed_only)
    metadata = update_manifest_index_metadata()

    return {
        "dry_run": False,
        "profile": asdict(profile),
        "manifest_embedding": {
            "provider": profile.provider,
            "model": profile.model,
            "dimensions": profile.dimensions,
            "normalised": profile.normalised,
        },
        "index_metadata": metadata,
    }


def profiles_as_dict(profiles: list[EmbeddingProfile]) -> list[dict[str, Any]]:
    return [asdict(profile) for profile in profiles]
