"""Reading-list generation for BookMem."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import re
from typing import Any

import yaml

from .router import route_query
from .search import search_books
from .summaries import search_summaries
from .concepts import search_concepts
from .topic_map import map_topic
from .book_graph import related_books
from .audit import append_audit_record
from .frontmatter import read_markdown_with_frontmatter


READING_LIST_VERSION = "0.1.0"
READING_LISTS_DIR = Path("data/reading-lists")


@dataclass
class ReadingListItem:
    rank: int
    title: str
    author: str | None
    book_id: str | None
    primary_class: str | None
    primary_label: str | None
    why: str
    evidence: list[str]
    suggested_posture: str
    reading_difficulty: str | None = None
    reading_density: str | None = None
    estimated_pages: int | None = None
    estimated_reading_hours: float | None = None
    best_read_as: str | None = None
    source_path: str | None = None


def normalise(value: str | None) -> str:
    value = (value or "").lower().strip()
    value = re.sub(r"^the\s+", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def intent_text(query: str | None = None, topic: str | None = None, goal: str | None = None) -> str:
    if goal:
        return goal
    if topic:
        return topic
    if query:
        return query
    raise ValueError("Provide a query, --topic or --goal.")


def _row_book_key(row: dict[str, Any]) -> str:
    return str(row.get("book_id") or f"{normalise(row.get('title'))}::{normalise(row.get('author'))}")


def _add_score(scores: dict[str, dict[str, Any]], row: dict[str, Any], amount: float, reason: str) -> None:
    key = _row_book_key(row)
    if not key or key == "::":
        return
    if key not in scores:
        scores[key] = {
            "book_id": row.get("book_id"),
            "title": row.get("title"),
            "author": row.get("author"),
            "primary_class": row.get("primary_class"),
            "primary_label": row.get("primary_label"),
            "source_path": row.get("source_path"),
            "score": 0.0,
            "evidence": [],
            "reasons": [],
        }
    scores[key]["score"] += amount
    if reason not in scores[key]["reasons"]:
        scores[key]["reasons"].append(reason)
    citation = row.get("citation") or row.get("heading_path")
    if citation and citation not in scores[key]["evidence"]:
        scores[key]["evidence"].append(str(citation))



def _reading_metadata_for_record(record: dict[str, Any]) -> dict[str, Any]:
    source = record.get("source_path")
    if not source:
        return {}
    path = Path(str(source))
    if not path.exists():
        return {}
    try:
        frontmatter, _body, _had = read_markdown_with_frontmatter(path)
        reading = frontmatter.get("reading") if isinstance(frontmatter.get("reading"), dict) else {}
        return reading
    except Exception:
        return {}



def _difficulty_posture(rank: int, title: str, reasons: list[str], reading: dict[str, Any] | None = None) -> str:
    reading = reading or {}
    best_read_as = reading.get("best_read_as")
    difficulty = reading.get("difficulty")
    density = reading.get("density")

    if rank == 1:
        return "Start here"
    if best_read_as == "reference":
        return "Use as a reference"
    if best_read_as == "skim_then_search":
        return "Skim, then search"
    if difficulty == "beginner":
        return "Read early"
    if difficulty == "advanced" or density == "dense":
        return "Read after the foundations"

    text = normalise(" ".join([title] + reasons))
    if any(term in text for term in ["beginner", "basics", "introduction", "simple"]):
        return "Read early"
    if any(term in text for term in ["advanced", "dense", "technical", "systems"]):
        return "Read after the foundations"
    if any(term in text for term in ["reference", "manual"]):
        return "Use as a reference"
    return "Then read"


def _why_for(record: dict[str, Any], intent: str) -> str:
    reasons = record.get("reasons", [])
    title = record.get("title") or "this book"
    bits = []
    if any("summary" in r for r in reasons):
        bits.append("summary match")
    if any("concept" in r for r in reasons):
        bits.append("contains relevant reusable concepts")
    if any("topic map" in r for r in reasons):
        bits.append("strong topic-map match")
    if any("search" in r for r in reasons):
        bits.append("relevant passages found")
    if any("graph" in r for r in reasons):
        bits.append("connected to other relevant books")
    if not bits:
        bits.append("matched the reading goal")
    return f"{title} is recommended for {intent} because it has " + ", ".join(bits) + "."


def generate_reading_list(
    query: str | None = None,
    *,
    topic: str | None = None,
    goal: str | None = None,
    limit: int = 8,
    save: bool = False,
    name: str | None = None,
) -> dict[str, Any]:
    intent = intent_text(query=query, topic=topic, goal=goal)
    scores: dict[str, dict[str, Any]] = {}
    route = {}
    warnings: list[str] = []

    try:
        route_obj = route_query(intent)
        if hasattr(route_obj, "model_dump"):
            route = route_obj.model_dump()
        elif hasattr(route_obj, "__dict__"):
            route = dict(route_obj.__dict__)
        elif isinstance(route_obj, dict):
            route = route_obj
    except Exception as exc:
        warnings.append(f"Routing failed: {exc}")

    class_codes = [str(v) for v in route.get("class_codes", []) or []]
    aliases = [str(v) for v in route.get("aliases", []) or []]

    # Passage search, scoped by route where available.
    searched = False
    for class_code in class_codes[:3]:
        try:
            for row in search_books(intent, limit=max(limit, 10), class_code=[class_code]):
                _add_score(scores, row, 3.0, f"routed search class {class_code}")
            searched = True
        except Exception as exc:
            warnings.append(f"Class search failed for {class_code}: {exc}")

    if not searched:
        try:
            for row in search_books(intent, limit=max(limit, 10)):
                _add_score(scores, row, 2.0, "broad search")
        except Exception as exc:
            warnings.append(f"Search failed: {exc}")

    # Summary matches.
    try:
        for row in search_summaries(intent, limit=max(limit, 10)):
            _add_score(scores, row, 2.5, "summary match")
    except Exception as exc:
        warnings.append(f"Summary search failed: {exc}")

    # Concept matches.
    try:
        for concept in search_concepts(intent, limit=max(limit, 10)):
            row = {
                "book_id": concept.get("book_id"),
                "title": concept.get("title"),
                "author": concept.get("author"),
                "primary_class": concept.get("primary_class"),
                "primary_label": concept.get("primary_label"),
                "source_path": None,
                "citation": f"Concept: {concept.get('name')}",
            }
            _add_score(scores, row, 2.0, "concept match")
    except Exception as exc:
        warnings.append(f"Concept search failed: {exc}")

    # Topic map strongest books.
    topic_map = None
    try:
        topic_map = map_topic(topic or goal or intent)
        strongest = topic_map.get("strongest_books", []) if isinstance(topic_map, dict) else []
        for idx, book in enumerate(strongest[:limit], start=1):
            row = {
                "book_id": book.get("book_id"),
                "title": book.get("title"),
                "author": book.get("author"),
                "primary_class": book.get("primary_class"),
                "primary_label": book.get("primary_label"),
                "source_path": book.get("source_path"),
                "citation": "topic map",
            }
            _add_score(scores, row, max(0.5, 2.0 - (idx * 0.1)), "topic map match")
    except Exception as exc:
        warnings.append(f"Topic map failed: {exc}")

    # Graph expansion from current top candidates.
    try:
        top_titles = [v.get("title") for v in sorted(scores.values(), key=lambda x: -x["score"])[:3] if v.get("title")]
        for title in top_titles:
            related = related_books(str(title), limit=4)
            for rel in related.get("related_books", []) if isinstance(related, dict) else []:
                row = {
                    "book_id": rel.get("book_id"),
                    "title": rel.get("title"),
                    "author": rel.get("author"),
                    "primary_class": rel.get("primary_class"),
                    "primary_label": rel.get("primary_label"),
                    "source_path": rel.get("source_path"),
                    "citation": f"related to {title}",
                }
                _add_score(scores, row, 0.75, "graph relationship")
    except Exception as exc:
        warnings.append(f"Graph expansion failed: {exc}")

    ranked = sorted(scores.values(), key=lambda item: (-item.get("score", 0), normalise(item.get("title"))))
    items = []
    for rank, record in enumerate(ranked[:limit], start=1):
        reading = _reading_metadata_for_record(record)
        items.append(
            ReadingListItem(
                rank=rank,
                title=str(record.get("title") or "Untitled"),
                author=record.get("author"),
                book_id=record.get("book_id"),
                primary_class=record.get("primary_class"),
                primary_label=record.get("primary_label"),
                why=_why_for(record, intent),
                evidence=record.get("evidence", [])[:5],
                suggested_posture=_difficulty_posture(rank, str(record.get("title") or ""), record.get("reasons", []), reading),
                reading_difficulty=reading.get("difficulty"),
                reading_density=reading.get("density"),
                estimated_pages=reading.get("estimated_pages"),
                estimated_reading_hours=reading.get("estimated_reading_hours"),
                best_read_as=reading.get("best_read_as"),
                source_path=record.get("source_path"),
            )
        )

    result = {
        "schema_version": 1,
        "reading_list_version": READING_LIST_VERSION,
        "query": query,
        "topic": topic,
        "goal": goal,
        "intent": intent,
        "route": route,
        "items": [asdict(item) for item in items],
        "topic_map": topic_map,
        "warnings": warnings,
    }

    if save:
        out_path = save_reading_list(result, name=name)
        result["saved_path"] = str(out_path)

    append_audit_record(
        action="reading_list.generate",
        status="ok" if items else "warn",
        changed_files=[result["saved_path"]] if result.get("saved_path") else [],
        target=name or intent,
        message=f"Generated reading list for: {intent}",
        details={"item_count": len(items), "saved": save},
    )

    return result


def save_reading_list(result: dict[str, Any], name: str | None = None) -> Path:
    READING_LISTS_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", (name or result.get("intent") or "reading-list").lower()).strip("-") or "reading-list"
    path = READING_LISTS_DIR / f"{slug}.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    md_path = path.with_suffix(".md")
    md_path.write_text(render_reading_list_markdown(result), encoding="utf-8")
    return path


def render_reading_list_markdown(result: dict[str, Any]) -> str:
    lines = [
        "---",
        "type: bookmem-reading-list",
        f"intent: {result.get('intent')}",
        "---",
        "",
        f"# Reading List — {result.get('intent')}",
        "",
    ]

    for item in result.get("items", []) or []:
        lines.append(f"## {item.get('rank')}. {item.get('suggested_posture')}: {item.get('title')}")
        lines.append("")
        if item.get("author"):
            lines.append(f"**Author:** {item.get('author')}")
        if item.get("primary_class"):
            lines.append(f"**Class:** {item.get('primary_class')} {item.get('primary_label') or ''}")
        lines.append("")
        lines.append(f"**Why:** {item.get('why')}")
        evidence = item.get("evidence") or []
        if evidence:
            lines.append("")
            lines.append("**Evidence:**")
            for ev in evidence:
                lines.append(f"- {ev}")
        lines.append("")

    if result.get("warnings"):
        lines.append("## Warnings")
        lines.append("")
        for warning in result["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")

    return "\n".join(lines)
