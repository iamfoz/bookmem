"""Lightweight plugin discovery for BookMem.

The first version is intentionally conservative: plugins are discovered from
YAML manifests and optional entrypoint metadata is validated, not executed.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import importlib.util
from typing import Any

import yaml


PLUGINS_VERSION = "0.1.0"
PLUGINS_DIR = Path("plugins")

PLUGIN_CATEGORIES = {
    "importers",
    "enrichers",
    "exporters",
    "summary_providers",
    "citation_styles",
}


@dataclass
class PluginManifest:
    id: str
    name: str
    category: str
    version: str
    description: str
    enabled: bool
    path: str
    capabilities: list[str]
    entrypoint_module: str | None = None
    entrypoint_object: str | None = None


def plugin_manifest_files(root: Path | None = None) -> list[Path]:
    root = root or PLUGINS_DIR
    if not root.exists():
        return []
    files: list[Path] = []
    for category in PLUGIN_CATEGORIES:
        category_dir = root / category
        if not category_dir.exists():
            continue
        files.extend(sorted(category_dir.glob("*.yaml")))
        files.extend(sorted(category_dir.glob("*.yml")))
        files.extend(sorted(category_dir.glob("*/plugin.yaml")))
        files.extend(sorted(category_dir.glob("*/plugin.yml")))

    # Deduplicate while preserving order.
    seen = set()
    out = []
    for path in files:
        key = str(path)
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


def load_plugin_manifest(path: Path) -> PluginManifest:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Plugin manifest must be a mapping: {path}")

    plugin = data.get("plugin")
    if not isinstance(plugin, dict):
        raise ValueError(f"Plugin manifest missing `plugin` mapping: {path}")

    entrypoint = plugin.get("entrypoint") if isinstance(plugin.get("entrypoint"), dict) else {}
    capabilities = plugin.get("capabilities") or []
    if not isinstance(capabilities, list):
        capabilities = [str(capabilities)]

    return PluginManifest(
        id=str(plugin.get("id") or path.stem),
        name=str(plugin.get("name") or plugin.get("id") or path.stem),
        category=str(plugin.get("category") or path.parent.name),
        version=str(plugin.get("version") or "0.0.0"),
        description=str(plugin.get("description") or ""),
        enabled=bool(plugin.get("enabled", False)),
        path=str(path),
        capabilities=[str(item) for item in capabilities],
        entrypoint_module=str(entrypoint.get("module")) if entrypoint.get("module") else None,
        entrypoint_object=str(entrypoint.get("object")) if entrypoint.get("object") else None,
    )


def discover_plugins(root: Path | None = None) -> list[PluginManifest]:
    plugins = []
    for path in plugin_manifest_files(root):
        plugins.append(load_plugin_manifest(path))
    return sorted(plugins, key=lambda p: (p.category, p.id))


def validate_plugins(root: Path | None = None) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for path in plugin_manifest_files(root):
        try:
            plugin = load_plugin_manifest(path)
        except Exception as exc:
            issues.append({
                "level": "error",
                "path": str(path),
                "plugin": None,
                "issue": "manifest_load",
                "message": str(exc),
            })
            continue

        if plugin.id in seen_ids:
            issues.append({
                "level": "error",
                "path": plugin.path,
                "plugin": plugin.id,
                "issue": "duplicate_id",
                "message": f"Duplicate plugin id: {plugin.id}",
            })
        seen_ids.add(plugin.id)

        if plugin.category not in PLUGIN_CATEGORIES:
            issues.append({
                "level": "error",
                "path": plugin.path,
                "plugin": plugin.id,
                "issue": "category",
                "message": f"Unknown plugin category: {plugin.category}",
            })

        if not plugin.capabilities:
            issues.append({
                "level": "warn",
                "path": plugin.path,
                "plugin": plugin.id,
                "issue": "capabilities",
                "message": "Plugin declares no capabilities.",
            })

        if plugin.enabled and not plugin.entrypoint_module:
            issues.append({
                "level": "warn",
                "path": plugin.path,
                "plugin": plugin.id,
                "issue": "entrypoint",
                "message": "Enabled plugin has no entrypoint module.",
            })

        if plugin.entrypoint_module:
            if importlib.util.find_spec(plugin.entrypoint_module) is None:
                issues.append({
                    "level": "warn",
                    "path": plugin.path,
                    "plugin": plugin.id,
                    "issue": "entrypoint_module",
                    "message": f"Entrypoint module is not importable in this environment: {plugin.entrypoint_module}",
                })

        if plugin.entrypoint_module and not plugin.entrypoint_object:
            issues.append({
                "level": "warn",
                "path": plugin.path,
                "plugin": plugin.id,
                "issue": "entrypoint_object",
                "message": "Entrypoint module is set but object is missing.",
            })

    return issues


def plugins_as_dict(plugins: list[PluginManifest]) -> list[dict[str, Any]]:
    return [asdict(plugin) for plugin in plugins]


def plugin_summary(root: Path | None = None) -> dict[str, Any]:
    plugins = discover_plugins(root)
    by_category: dict[str, int] = {category: 0 for category in sorted(PLUGIN_CATEGORIES)}
    enabled = 0
    for plugin in plugins:
        by_category[plugin.category] = by_category.get(plugin.category, 0) + 1
        if plugin.enabled:
            enabled += 1

    return {
        "plugins_version": PLUGINS_VERSION,
        "root": str(root or PLUGINS_DIR),
        "total": len(plugins),
        "enabled": enabled,
        "by_category": by_category,
        "plugins": plugins_as_dict(plugins),
    }
