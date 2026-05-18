from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .config import get_settings


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, Any]:
    settings = get_settings()
    if not settings.taxonomy_path.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {settings.taxonomy_path}")
    return yaml.safe_load(settings.taxonomy_path.read_text(encoding="utf-8"))


def normalise_alias(alias: str) -> str:
    return alias.strip().lower().replace(" ", "_").replace("-", "_")


def get_class_label(class_code: str | None) -> str:
    if not class_code:
        return "Unclassified"
    taxonomy = load_taxonomy()
    return taxonomy.get("classes", {}).get(str(class_code), {}).get("label", "Unknown")


def infer_class_from_path(path: Path, books_dir: Path) -> tuple[str, str]:
    """Infer a BMDC class from a folder such as 332-financial-economics-finance."""
    try:
        relative = path.relative_to(books_dir)
    except ValueError:
        return "999", "Unclassified"

    if len(relative.parts) < 2:
        return "999", "Unclassified"

    folder = relative.parts[0]
    code = folder.split("-", 1)[0]
    if code.isdigit() and len(code) == 3:
        return code, get_class_label(code)

    return "999", "Unclassified"


def resolve_alias(alias: str) -> dict[str, list[str]]:
    taxonomy = load_taxonomy()
    aliases = taxonomy.get("routing_aliases", {})
    resolved = aliases.get(normalise_alias(alias), {"primary_class": [], "secondary_class": []})

    return resolved


def all_routing_aliases() -> list[str]:
    taxonomy = load_taxonomy()
    return sorted(taxonomy.get("routing_aliases", {}).keys())
