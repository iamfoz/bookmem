"""Saved queries and recurring research briefs for BookMem."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Any

import yaml

from .answer_pack import build_answer_pack
from .workspaces import workspace_answer_pack
from .concepts import search_concepts
from .topic_maps import map_topic
from .manifest import load_manifest
from .audit import append_audit_record


SAVED_QUERY_VERSION = "0.1.0"
QUERIES_DIR = Path("data/queries")
BRIEFS_DIR = Path("data/briefs")


@dataclass
class SavedQuery:
    name: str
    query: str
    workspace: str | None
    description: str | None
    tags: list[str]
    limit: int
    context: int
    include_concepts: bool
    include_topic_map: bool
    include_changed_since_last_run: bool
    created_at: str | None = None
    last_run_at: str | None = None
    schema_version: int = 1


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "query"


def query_path(name: str) -> Path:
    return QUERIES_DIR / f"{slugify(name)}.yaml"


def brief_dir(name: str) -> Path:
    return BRIEFS_DIR / slugify(name)


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if value:
        return [str(value)]
    return []


def saved_query_from_dict(data: dict[str, Any]) -> SavedQuery:
    return SavedQuery(
        name=str(data.get("name") or slugify(data.get("query") or "query")),
        query=str(data.get("query") or ""),
        workspace=str(data.get("workspace")) if data.get("workspace") else None,
        description=str(data.get("description")) if data.get("description") else None,
        tags=_list(data.get("tags")),
        limit=int(data.get("limit") or 8),
        context=int(data.get("context") or 1),
        include_concepts=bool(data.get("include_concepts", True)),
        include_topic_map=bool(data.get("include_topic_map", True)),
        include_changed_since_last_run=bool(data.get("include_changed_since_last_run", True)),
        created_at=data.get("created_at"),
        last_run_at=data.get("last_run_at"),
        schema_version=int(data.get("schema_version") or 1),
    )


def save_query(
    query: str,
    name: str | None = None,
    workspace: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    limit: int = 8,
    context: int = 1,
    overwrite: bool = False,
) -> SavedQuery:
    QUERIES_DIR.mkdir(parents=True, exist_ok=True)
    name = slugify(name or query)
    path = query_path(name)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Saved query already exists: {path}. Use --overwrite to replace it.")

    sq = SavedQuery(
        name=name,
        query=query,
        workspace=workspace,
        description=description,
        tags=tags or [],
        limit=limit,
        context=context,
        include_concepts=True,
        include_topic_map=True,
        include_changed_since_last_run=True,
        created_at=utc_now_iso(),
        last_run_at=None,
    )
    path.write_text(yaml.safe_dump(asdict(sq), sort_keys=False, allow_unicode=True), encoding="utf-8")
    append_audit_record(
        action="query.save",
        status="ok",
        changed_files=[path],
        target=name,
        message=f"Saved query {name}",
        details={"query": query, "workspace": workspace},
    )
    return sq


def load_saved_query(name: str) -> SavedQuery:
    path = query_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Saved query not found: {name}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return saved_query_from_dict(data)


def write_saved_query(saved: SavedQuery) -> None:
    QUERIES_DIR.mkdir(parents=True, exist_ok=True)
    query_path(saved.name).write_text(yaml.safe_dump(asdict(saved), sort_keys=False, allow_unicode=True), encoding="utf-8")


def list_saved_queries() -> list[dict[str, Any]]:
    QUERIES_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for path in sorted(QUERIES_DIR.glob("*.yaml")):
        try:
            sq = saved_query_from_dict(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
            row = asdict(sq)
            row["path"] = str(path)
            out.append(row)
        except Exception as exc:
            out.append({"name": path.stem, "path": str(path), "error": str(exc)})
    return out


def changed_since(timestamp: str | None) -> dict[str, Any]:
    if not timestamp:
        return {"since": None, "books": [], "summaries": []}

    manifest = load_manifest()
    books = []
    summaries = []
    for record in manifest.get("books", []) or []:
        if not isinstance(record, dict):
            continue
        prepared = record.get("last_prepared")
        indexed = record.get("last_indexed")
        summarised = record.get("last_summarised")
        title = record.get("title") or record.get("book_id") or record.get("canonical_path")
        if prepared and str(prepared) > timestamp:
            books.append({"book_id": record.get("book_id"), "title": title, "changed_at": prepared, "change": "prepared"})
        if indexed and str(indexed) > timestamp:
            books.append({"book_id": record.get("book_id"), "title": title, "changed_at": indexed, "change": "indexed"})
        if summarised and str(summarised) > timestamp:
            summaries.append({"book_id": record.get("book_id"), "title": title, "changed_at": summarised, "change": "summarised"})

    return {"since": timestamp, "books": books, "summaries": summaries}


def run_saved_query(name: str, update_last_run: bool = False) -> dict[str, Any]:
    saved = load_saved_query(name)
    if saved.workspace:
        pack = workspace_answer_pack(saved.workspace, saved.query, limit=saved.limit, context=saved.context)
    else:
        pack = build_answer_pack(saved.query, limit=saved.limit, context=saved.context)

    result = {
        "saved_query": asdict(saved),
        "answer_pack": pack,
    }

    if update_last_run:
        saved.last_run_at = utc_now_iso()
        write_saved_query(saved)

    return result


def generate_brief(name: str, update_last_run: bool = True, markdown: bool = True) -> dict[str, Any]:
    saved = load_saved_query(name)
    previous_run = saved.last_run_at

    if saved.workspace:
        pack = workspace_answer_pack(saved.workspace, saved.query, limit=saved.limit, context=saved.context)
    else:
        pack = build_answer_pack(saved.query, limit=saved.limit, context=saved.context)

    concepts = []
    if saved.include_concepts:
        try:
            concepts = search_concepts(saved.query, limit=saved.limit)
        except Exception as exc:
            concepts = [{"error": str(exc)}]

    topic = None
    if saved.include_topic_map:
        try:
            topic = map_topic(saved.query).to_dict()
        except Exception as exc:
            topic = {"error": str(exc)}

    changes = changed_since(previous_run) if saved.include_changed_since_last_run else {"since": previous_run, "books": [], "summaries": []}

    generated_at = utc_now_iso()
    brief = {
        "schema_version": 1,
        "brief_version": SAVED_QUERY_VERSION,
        "generated_at": generated_at,
        "saved_query": asdict(saved),
        "best_books": pack.get("relevant_books", []),
        "top_passages": pack.get("top_passages", []),
        "related_concepts": concepts,
        "topic_map": topic,
        "changed_since_last_run": changes,
        "suggested_synthesis": pack.get("suggested_synthesis"),
        "citations": pack.get("citations", []),
        "answer_pack": pack,
    }

    out_dir = brief_dir(saved.name)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{generated_at.replace(':', '').replace('+00:00', 'Z')}.json"
    json_path.write_text(json.dumps(brief, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

    md_path = None
    if markdown:
        md_path = json_path.with_suffix(".md")
        md_path.write_text(render_brief_markdown(brief), encoding="utf-8")

    if update_last_run:
        saved.last_run_at = generated_at
        write_saved_query(saved)

    append_audit_record(
        action="brief.generate",
        status="ok",
        changed_files=[json_path] + ([md_path] if md_path else []),
        target=saved.name,
        message=f"Generated brief for saved query {saved.name}",
        details={"query": saved.query, "workspace": saved.workspace, "previous_run": previous_run},
    )

    return {
        "brief": brief,
        "json_path": str(json_path),
        "markdown_path": str(md_path) if md_path else None,
    }


def render_brief_markdown(brief: dict[str, Any]) -> str:
    sq = brief["saved_query"]
    lines = [
        "---",
        "type: bookmem-brief",
        f"name: {sq.get('name')}",
        f"query: {sq.get('query')}",
        f"workspace: {sq.get('workspace') or ''}",
        f"generated_at: {brief.get('generated_at')}",
        "---",
        "",
        f"# Research Brief — {sq.get('name')}",
        "",
        f"**Query:** {sq.get('query')}",
        "",
    ]

    if sq.get("workspace"):
        lines.append(f"**Workspace:** {sq.get('workspace')}")
        lines.append("")

    lines += ["## Best books", ""]
    for index, book in enumerate(brief.get("best_books", []) or [], start=1):
        lines.append(f"{index}. **{book.get('title') or ''}** — {book.get('author') or ''}")
        if book.get("primary_class"):
            lines.append(f"   - Class: {book.get('primary_class')} {book.get('primary_label') or ''}")
    if not brief.get("best_books"):
        lines.append("_No books found._")
    lines.append("")

    lines += ["## Top passages", ""]
    for index, passage in enumerate(brief.get("top_passages", []) or [], start=1):
        lines.append(f"### {index}. {passage.get('title') or 'Untitled'}")
        lines.append("")
        if passage.get("heading_path"):
            lines.append(f"**Location:** {passage.get('heading_path')}")
        if passage.get("citation"):
            lines.append(f"**Citation:** {passage.get('citation')}")
        excerpt = passage.get("excerpt") or passage.get("text") or ""
        if excerpt:
            lines.append("")
            lines.append(str(excerpt)[:1000])
        lines.append("")
    if not brief.get("top_passages"):
        lines.append("_No passages found._")
        lines.append("")

    lines += ["## Related concepts", ""]
    for concept in brief.get("related_concepts", []) or []:
        if concept.get("error"):
            lines.append(f"- Error: {concept['error']}")
            continue
        lines.append(f"- **{concept.get('name') or ''}** ({concept.get('type') or 'concept'}) — {concept.get('title') or ''}")
        if concept.get("description"):
            lines.append(f"  - {concept.get('description')}")
    if not brief.get("related_concepts"):
        lines.append("_No related concepts found._")
    lines.append("")

    changes = brief.get("changed_since_last_run") or {}
    lines += ["## Newly added or changed since last run", ""]
    since = changes.get("since")
    lines.append(f"Since: {since or 'first run / no previous run'}")
    lines.append("")
    for item in changes.get("books", [])[:20]:
        lines.append(f"- {item.get('change')}: {item.get('title')} ({item.get('changed_at')})")
    for item in changes.get("summaries", [])[:20]:
        lines.append(f"- {item.get('change')}: {item.get('title')} ({item.get('changed_at')})")
    if not changes.get("books") and not changes.get("summaries"):
        lines.append("_No changed books or summaries detected._")
    lines.append("")

    lines += ["## Suggested synthesis", ""]
    synth = brief.get("suggested_synthesis") or {}
    for point in synth.get("possible_synthesis_points", []) or []:
        lines.append(f"- {point}")
    if synth.get("recurring_themes"):
        lines.append("")
        lines.append("Recurring themes:")
        for theme in synth.get("recurring_themes", [])[:12]:
            lines.append(f"- {theme}")
    lines.append("")

    lines += ["## Citations", ""]
    for citation in brief.get("citations", []) or []:
        lines.append(f"- {citation}")
    if not brief.get("citations"):
        lines.append("_No citations found._")
    lines.append("")

    return "\n".join(lines)
