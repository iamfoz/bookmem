"""Book-to-book relationship graph for BookMem."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Any

import yaml

from .config import get_settings
from .frontmatter import discover_book_files, read_markdown_with_frontmatter
from .editions import slugify as edition_slugify


GRAPH_SCHEMA_VERSION = 1
GRAPH_VERSION = "0.1.0"


@dataclass
class BookNode:
    book_id: str
    title: str
    author: str | None
    path: str
    primary_class: str | None
    primary_label: str | None
    topics: list[str]
    routing_aliases: list[str]
    work_id: str | None
    canonical_title: str | None
    edition_label: str | None


@dataclass
class BookEdge:
    source: str
    target: str
    score: float
    reasons: list[str]
    shared_topics: list[str]
    relationship_types: list[str]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalise_token(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def token_set(values: list[Any]) -> set[str]:
    out = set()
    for value in values or []:
        text = normalise_token(str(value))
        if text:
            out.add(text)
    return out


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if value:
        return [str(value).strip()]
    return []


def _book_id(frontmatter: dict[str, Any], path: Path) -> str:
    if frontmatter.get("book_id"):
        return str(frontmatter["book_id"])
    title = str(frontmatter.get("title") or path.stem)
    author = str(frontmatter.get("author") or "")
    raw = f"{author}_{title}" if author else title
    return edition_slugify(raw)


def node_from_book(path: Path) -> BookNode:
    frontmatter, _body, _had = read_markdown_with_frontmatter(path)
    classification = frontmatter.get("classification") if isinstance(frontmatter.get("classification"), dict) else {}
    work = frontmatter.get("work") if isinstance(frontmatter.get("work"), dict) else {}
    edition = frontmatter.get("edition") if isinstance(frontmatter.get("edition"), dict) else {}

    topics = _list(classification.get("topics")) or _list(frontmatter.get("tags"))
    aliases = _list(classification.get("routing_aliases"))

    return BookNode(
        book_id=_book_id(frontmatter, path),
        title=str(frontmatter.get("title") or path.stem),
        author=str(frontmatter.get("author")) if frontmatter.get("author") else None,
        path=str(path),
        primary_class=str(classification.get("primary_class")) if classification.get("primary_class") else None,
        primary_label=str(classification.get("primary_label")) if classification.get("primary_label") else None,
        topics=topics,
        routing_aliases=aliases,
        work_id=str(work.get("work_id")) if work.get("work_id") else None,
        canonical_title=str(work.get("canonical_title")) if work.get("canonical_title") else None,
        edition_label=str(edition.get("label")) if edition.get("label") else None,
    )


def load_summary_terms(book_id: str) -> set[str]:
    path = Path("data/summaries") / book_id / "book.yaml"
    if not path.exists():
        return set()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return set()

    terms: list[str] = []
    for key in ("major_ideas", "best_for_questions_about", "topics", "themes"):
        value = data.get(key)
        if isinstance(value, list):
            terms.extend(str(v) for v in value)
        elif value:
            terms.append(str(value))
    if data.get("core_thesis"):
        # Keep only substantial terms from the thesis.
        thesis = re.sub(r"[^a-zA-Z0-9\s-]", " ", str(data["core_thesis"]))
        terms.extend(word for word in thesis.split() if len(word) > 5)

    return token_set(terms)


def edge_between(
    a: BookNode,
    b: BookNode,
    summary_terms: dict[str, set[str]] | None = None,
) -> BookEdge | None:
    score = 0.0
    reasons: list[str] = []
    relationship_types: list[str] = []
    shared_topics = sorted(token_set(a.topics) & token_set(b.topics))

    if a.book_id == b.book_id:
        return None

    if a.work_id and b.work_id and a.work_id == b.work_id:
        score += 0.95
        relationship_types.append("same_work")
        reasons.append("same work/edition group")

    if a.author and b.author and normalise_token(a.author) == normalise_token(b.author):
        score += 0.35
        relationship_types.append("same_author")
        reasons.append("same author")

    if a.primary_class and b.primary_class and a.primary_class == b.primary_class:
        score += 0.25
        relationship_types.append("same_class")
        reasons.append(f"same class {a.primary_class}")

    if shared_topics:
        topic_score = min(0.5, 0.12 * len(shared_topics))
        score += topic_score
        relationship_types.append("same_topics")
        reasons.append("shared topics: " + ", ".join(shared_topics[:6]))

    alias_shared = sorted(token_set(a.routing_aliases) & token_set(b.routing_aliases))
    if alias_shared:
        score += min(0.35, 0.1 * len(alias_shared))
        relationship_types.append("same_routing_aliases")
        reasons.append("shared routing aliases: " + ", ".join(alias_shared[:6]))

    if summary_terms is not None:
        a_terms = summary_terms.get(a.book_id, set())
        b_terms = summary_terms.get(b.book_id, set())
    else:
        a_terms = load_summary_terms(a.book_id)
        b_terms = load_summary_terms(b.book_id)
    summary_shared = sorted(a_terms & b_terms)
    if summary_shared:
        score += min(0.45, 0.08 * len(summary_shared))
        relationship_types.append("similar_summaries")
        reasons.append("similar summaries: " + ", ".join(summary_shared[:6]))

    if score <= 0:
        return None

    return BookEdge(
        source=a.book_id,
        target=b.book_id,
        score=round(min(score, 1.0), 3),
        reasons=reasons,
        shared_topics=shared_topics,
        relationship_types=relationship_types,
    )


def build_book_graph(books_dir: Path | None = None, output_path: Path | None = None, min_score: float = 0.2) -> dict[str, Any]:
    settings = get_settings()
    books_dir = books_dir or settings.books_dir
    output_path = output_path or Path("data/graphs/book_graph.json")

    nodes = [node_from_book(path) for path in discover_book_files(books_dir)]
    summary_terms = {node.book_id: load_summary_terms(node.book_id) for node in nodes}
    edges: list[BookEdge] = []

    for index, node_a in enumerate(nodes):
        for node_b in nodes[index + 1:]:
            edge = edge_between(node_a, node_b, summary_terms)
            if edge and edge.score >= min_score:
                edges.append(edge)

    payload = {
        "schema_version": GRAPH_SCHEMA_VERSION,
        "graph_version": GRAPH_VERSION,
        "generated_at": utc_now_iso(),
        "books_dir": str(books_dir),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": [asdict(node) for node in nodes],
        "edges": [asdict(edge) for edge in sorted(edges, key=lambda e: e.score, reverse=True)],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def load_book_graph(path: Path | None = None) -> dict[str, Any]:
    path = path or Path("data/graphs/book_graph.json")
    if not path.exists():
        return build_book_graph(output_path=path)
    return json.loads(path.read_text(encoding="utf-8"))


def _matches_query(node: dict[str, Any], query: str) -> bool:
    q = normalise_token(query)
    haystack = " ".join([
        str(node.get("book_id") or ""),
        str(node.get("title") or ""),
        str(node.get("author") or ""),
        str(node.get("canonical_title") or ""),
        " ".join(node.get("topics") or []),
        " ".join(node.get("routing_aliases") or []),
    ])
    return q in normalise_token(haystack)


def related_books(query: str | None = None, topic: str | None = None, limit: int = 10, graph_path: Path | None = None) -> dict[str, Any]:
    graph = load_book_graph(graph_path)
    nodes = {node["book_id"]: node for node in graph.get("nodes", [])}
    edges = graph.get("edges", [])

    scored: dict[str, dict[str, Any]] = {}

    if topic:
        topic_norm = normalise_token(topic)
        for node_id, node in nodes.items():
            topic_terms = token_set((node.get("topics") or []) + (node.get("routing_aliases") or []))
            summary_terms = load_summary_terms(node_id)
            reasons = []
            score = 0.0
            matches = [term for term in sorted(topic_terms | summary_terms) if topic_norm in term or term in topic_norm]
            if matches:
                score += min(1.0, 0.25 + 0.12 * len(matches))
                reasons.append("topic match: " + ", ".join(matches[:6]))
            if score:
                scored[node_id] = {"node": node, "score": round(score, 3), "reasons": reasons, "relationship_types": ["topic_match"]}

    elif query:
        seed_ids = [node_id for node_id, node in nodes.items() if _matches_query(node, query)]
        if not seed_ids:
            # Fall back to topic-like behaviour.
            return related_books(topic=query, limit=limit, graph_path=graph_path)

        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            other = None
            if source in seed_ids:
                other = target
            elif target in seed_ids:
                other = source
            if not other or other not in nodes:
                continue

            existing = scored.get(other)
            score = float(edge.get("score", 0))
            reasons = list(edge.get("reasons") or [])
            relationship_types = list(edge.get("relationship_types") or [])
            if existing:
                existing["score"] = max(existing["score"], score)
                existing["reasons"] = sorted(set(existing["reasons"] + reasons))
                existing["relationship_types"] = sorted(set(existing["relationship_types"] + relationship_types))
            else:
                scored[other] = {"node": nodes[other], "score": score, "reasons": reasons, "relationship_types": relationship_types}

    items = sorted(scored.values(), key=lambda item: item["score"], reverse=True)[:limit]
    return {
        "query": query,
        "topic": topic,
        "graph_path": str(graph_path or Path("data/graphs/book_graph.json")),
        "count": len(items),
        "related": items,
    }
