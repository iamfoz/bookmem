"""Workspace/project views for scoped BookMem retrieval."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
from typing import Any

import yaml

from .search import search_books
from .answer_pack import build_answer_pack


WORKSPACES_VERSION = "0.1.0"
DEFAULT_WORKSPACES_PATH = Path("config/workspaces.yaml")


@dataclass
class Workspace:
    name: str
    label: str
    description: str
    classes: list[str]
    topics: list[str]
    aliases: list[str]


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if value:
        return [str(value)]
    return []


def load_workspaces(path: Path | None = None) -> dict[str, Workspace]:
    path = path or DEFAULT_WORKSPACES_PATH
    if not path.exists():
        return {}

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = data.get("workspaces", {}) if isinstance(data, dict) else {}
    if not isinstance(raw, dict):
        raise ValueError("config/workspaces.yaml must contain a workspaces mapping.")

    workspaces: dict[str, Workspace] = {}
    for name, cfg in raw.items():
        if not isinstance(cfg, dict):
            continue
        workspaces[str(name)] = Workspace(
            name=str(name),
            label=str(cfg.get("label") or name),
            description=str(cfg.get("description") or ""),
            classes=_list(cfg.get("classes")),
            topics=_list(cfg.get("topics")),
            aliases=_list(cfg.get("aliases")),
        )
    return workspaces


def get_workspace(name: str) -> Workspace:
    workspaces = load_workspaces()
    if name not in workspaces:
        raise KeyError(f"Unknown workspace: {name}")
    return workspaces[name]


def workspace_query_text(workspace: Workspace, query: str) -> str:
    # Keep the original user query central, but add workspace terms for broad fallback searches.
    terms = workspace.topics[:8] + workspace.aliases[:5]
    if terms:
        return f"{query} " + " ".join(terms)
    return query


def workspace_search(name: str, query: str, limit: int = 10) -> dict[str, Any]:
    workspace = get_workspace(name)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    # First search by class scope.
    for class_code in workspace.classes:
        try:
            for row in search_books(query=query, limit=limit, class_code=[class_code]):
                key = str(row.get("chunk_id") or json.dumps(row, sort_keys=True, default=str))
                if key not in seen:
                    seen.add(key)
                    rows.append(row)
                if len(rows) >= limit:
                    break
        except Exception:
            continue
        if len(rows) >= limit:
            break

    # Then search by aliases if needed.
    if len(rows) < limit:
        for alias in workspace.aliases:
            try:
                for row in search_books(query=query, limit=limit, alias=[alias]):
                    key = str(row.get("chunk_id") or json.dumps(row, sort_keys=True, default=str))
                    if key not in seen:
                        seen.add(key)
                        rows.append(row)
                    if len(rows) >= limit:
                        break
            except Exception:
                continue
            if len(rows) >= limit:
                break

    # Final fallback uses topic-enriched query. We still keep results that match workspace classes/topics better.
    if len(rows) < limit:
        try:
            for row in search_books(query=workspace_query_text(workspace, query), limit=limit):
                key = str(row.get("chunk_id") or json.dumps(row, sort_keys=True, default=str))
                if key not in seen:
                    seen.add(key)
                    rows.append(row)
                if len(rows) >= limit:
                    break
        except Exception:
            pass

    return {
        "workspace": asdict(workspace),
        "query": query,
        "limit": limit,
        "count": len(rows[:limit]),
        "results": rows[:limit],
    }


def workspace_answer_pack(
    name: str,
    query: str,
    limit: int = 6,
    context: int = 1,
    include_text: bool = True,
) -> dict[str, Any]:
    workspace = get_workspace(name)
    scoped = workspace_search(name, query, limit=limit)

    # Build a normal answer pack too, but annotate and replace top passages with scoped hits when available.
    pack = build_answer_pack(
        query=query,
        limit=limit,
        context=context,
        summaries_first=True,
        include_text=include_text,
    )
    pack["workspace"] = asdict(workspace)
    pack["workspace_query"] = query
    pack["workspace_results"] = scoped["results"]

    if scoped["results"]:
        # Keep the original pack structure but make it obvious these are the scoped candidates.
        pack["relevant_books"] = _unique_books(scoped["results"])
        pack["top_passages"] = scoped["results"]
        pack["suggested_synthesis"]["note"] = (
            "This answer pack was scoped to a workspace. Use workspace_results/top_passages before considering broader corpus evidence."
        )

    return pack


def _unique_books(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    books = []
    for row in rows:
        key = row.get("book_id") or f"{row.get('title')}::{row.get('author')}"
        if key in seen:
            continue
        seen.add(key)
        books.append(
            {
                "book_id": row.get("book_id"),
                "title": row.get("title"),
                "author": row.get("author"),
                "primary_class": row.get("primary_class"),
                "primary_label": row.get("primary_label"),
                "source_path": row.get("source_path"),
            }
        )
    return books


def list_workspaces_as_dict() -> list[dict[str, Any]]:
    return [asdict(ws) for ws in load_workspaces().values()]


def validate_workspaces(path: Path | None = None) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    workspaces = load_workspaces(path)
    for name, workspace in workspaces.items():
        if not workspace.classes and not workspace.topics and not workspace.aliases:
            issues.append({"workspace": name, "level": "warn", "message": "Workspace has no classes, topics or aliases."})
        for class_code in workspace.classes:
            if not class_code.isdigit():
                issues.append({"workspace": name, "level": "warn", "message": f"Class code is not numeric: {class_code}"})
    return issues
