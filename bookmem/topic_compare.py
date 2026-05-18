"""Contradiction/disagreement mapping for BookMem topics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import re
from typing import Any

from .search import search_books
from .summaries import search_summaries
from .passages import search_passages
from .audit import append_audit_record


TOPIC_COMPARE_VERSION = "0.1.0"

FAVOUR_TERMS = {
    "benefit", "benefits", "useful", "effective", "important", "valuable",
    "helpful", "supports", "improves", "works", "advantage", "strength",
    "should", "must", "essential", "positive", "success", "clarity",
    "focus", "direction", "motivation", "goal", "goals",
}

CRITIQUE_TERMS = {
    "problem", "problems", "risk", "risks", "danger", "dangerous",
    "fails", "failure", "weakness", "limits", "limited", "misleading",
    "criticise", "criticizes", "criticising", "criticizing", "avoid",
    "trap", "drawback", "negative", "counterproductive", "worse",
    "instead", "rather than", "not enough", "system", "systems",
}

TENSION_PATTERNS = [
    ("direction", "execution", "Direction can help choose a path, but execution depends on repeatable behaviour."),
    ("goal", "system", "Goals can direct attention, but systems drive repeatable behaviour."),
    ("motivation", "habit", "Motivation can start action, but habits and environment sustain it."),
    ("risk", "return", "Higher return may require accepting more risk, but unmanaged risk can destroy compounding."),
    ("simplicity", "complexity", "Simplification aids action, but complex domains may require nuance."),
    ("planning", "feedback", "Planning creates intent, but feedback shows whether the plan survives reality."),
]


@dataclass
class TopicStance:
    book_id: str | None
    title: str | None
    author: str | None
    stance: str
    score: int
    reason: str
    evidence: list[str]
    citations: list[str]
    source: str


def normalise(text: str | None) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def stance_for_text(topic: str, text: str) -> tuple[str, int, str]:
    haystack = normalise(text)
    topic_terms = [term for term in normalise(topic).split() if len(term) > 2]

    fav = sum(1 for term in FAVOUR_TERMS if term in haystack)
    crit = sum(1 for term in CRITIQUE_TERMS if term in haystack)
    topic_hits = sum(1 for term in topic_terms if term in haystack)

    # Handle common "systems vs goals" type framing.
    if "rather than" in haystack or "instead of" in haystack or "versus" in haystack:
        crit += 1

    if fav > crit + 1:
        return "favouring", fav + topic_hits, "Language is more supportive/affirming than critical."
    if crit > fav + 1:
        return "criticising", crit + topic_hits, "Language is more critical/cautionary than supportive."
    if fav and crit:
        return "mixed", fav + crit + topic_hits, "Evidence contains both supportive and critical language."
    return "neutral", topic_hits, "No strong stance detected; useful as neutral context."


def _add_record(
    grouped: dict[str, dict[str, Any]],
    *,
    row: dict[str, Any],
    stance: str,
    score: int,
    reason: str,
    evidence_text: str,
    citation: str | None,
    source: str,
) -> None:
    key = str(row.get("book_id") or f"{row.get('title')}::{row.get('author')}")
    if not key or key == "::":
        return
    item = grouped.setdefault(
        key,
        {
            "book_id": row.get("book_id"),
            "title": row.get("title"),
            "author": row.get("author"),
            "stance_scores": defaultdict(int),
            "evidence": [],
            "citations": [],
            "sources": set(),
            "reasons": set(),
        },
    )
    item["stance_scores"][stance] += max(score, 1)
    excerpt = re.sub(r"\s+", " ", evidence_text or "").strip()[:600]
    if excerpt and excerpt not in item["evidence"]:
        item["evidence"].append(excerpt)
    if citation and citation not in item["citations"]:
        item["citations"].append(citation)
    item["sources"].add(source)
    item["reasons"].add(reason)


def _finalise(grouped: dict[str, dict[str, Any]]) -> list[TopicStance]:
    out = []
    for item in grouped.values():
        scores = dict(item["stance_scores"])
        if not scores:
            stance = "neutral"
            score = 0
        else:
            stance = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            score = scores[stance]
        out.append(
            TopicStance(
                book_id=item.get("book_id"),
                title=item.get("title"),
                author=item.get("author"),
                stance=stance,
                score=score,
                reason="; ".join(sorted(item["reasons"]))[:500],
                evidence=item["evidence"][:5],
                citations=item["citations"][:5],
                source=", ".join(sorted(item["sources"])),
            )
        )
    return sorted(out, key=lambda row: (-row.score, row.title or ""))


def infer_tensions(topic: str, stances: list[TopicStance]) -> list[str]:
    topic_norm = normalise(topic)
    tensions = []

    for a, b, text in TENSION_PATTERNS:
        if a in topic_norm or b in topic_norm:
            tensions.append(text)

    has_favour = any(s.stance == "favouring" for s in stances)
    has_crit = any(s.stance == "criticising" for s in stances)
    has_mixed = any(s.stance == "mixed" for s in stances)

    if has_favour and has_crit:
        tensions.append(f"Some books treat {topic} as useful, while others frame it as limited or potentially misleading.")
    if has_mixed:
        tensions.append(f"At least one source appears to treat {topic} as context-dependent rather than simply good or bad.")
    if not tensions:
        tensions.append(f"The current corpus evidence does not show a strong disagreement pattern for {topic}; treat this as a weak or emerging map.")

    # Deduplicate while preserving order.
    seen = set()
    deduped = []
    for tension in tensions:
        if tension not in seen:
            seen.add(tension)
            deduped.append(tension)
    return deduped[:8]


def compare_topic(topic: str, limit: int = 12) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}

    # Passages layer first because it is closest to curated evidence.
    try:
        for row in search_passages(topic, limit=limit * 2):
            text = " ".join(str(row.get(k) or "") for k in ("quote", "summary", "why_it_matters"))
            stance, score, reason = stance_for_text(topic, text)
            _add_record(
                grouped,
                row=row,
                stance=stance,
                score=score + 2,
                reason=reason,
                evidence_text=text,
                citation=row.get("citation"),
                source="passages",
            )
    except Exception:
        pass

    # Summaries provide book-level map.
    try:
        for row in search_summaries(topic, limit=limit * 2):
            text = " ".join(str(row.get(k) or "") for k in ("core_thesis", "summary", "major_ideas", "best_for_questions_about", "text"))
            stance, score, reason = stance_for_text(topic, text)
            _add_record(
                grouped,
                row=row,
                stance=stance,
                score=score + 1,
                reason=reason,
                evidence_text=text,
                citation=row.get("citation"),
                source="summaries",
            )
    except Exception:
        pass

    # Chunk search provides direct evidence.
    try:
        for row in search_books(topic, limit=limit * 3):
            text = str(row.get("text") or row.get("excerpt") or "")
            stance, score, reason = stance_for_text(topic, text)
            _add_record(
                grouped,
                row=row,
                stance=stance,
                score=score,
                reason=reason,
                evidence_text=text,
                citation=row.get("citation"),
                source="search",
            )
    except Exception:
        pass

    stances = _finalise(grouped)
    favouring = [asdict(s) for s in stances if s.stance == "favouring"][:limit]
    criticising = [asdict(s) for s in stances if s.stance == "criticising"][:limit]
    mixed = [asdict(s) for s in stances if s.stance == "mixed"][:limit]
    neutral = [asdict(s) for s in stances if s.stance == "neutral"][:limit]

    result = {
        "schema_version": 1,
        "topic_compare_version": TOPIC_COMPARE_VERSION,
        "topic": topic,
        "books_favouring": favouring,
        "books_criticising": criticising,
        "books_mixed": mixed,
        "books_neutral": neutral,
        "tensions": infer_tensions(topic, stances),
        "method": "deterministic stance heuristic over passages, summaries and chunk search",
        "review_status": "machine_draft",
    }

    append_audit_record(
        action="topic.compare",
        status="ok",
        changed_files=[],
        target=topic,
        message=f"Compared topic stances for {topic}",
        details={
            "favouring": len(favouring),
            "criticising": len(criticising),
            "mixed": len(mixed),
            "neutral": len(neutral),
        },
    )

    return result


def render_compare_markdown(result: dict[str, Any]) -> str:
    lines = [
        "---",
        "type: bookmem-topic-comparison",
        f"topic: {result.get('topic')}",
        f"review_status: {result.get('review_status')}",
        "---",
        "",
        f"# Topic Comparison — {result.get('topic')}",
        "",
        "## Books favouring",
        "",
    ]

    def add_section(rows: list[dict[str, Any]]):
        if not rows:
            lines.append("_None found._")
            lines.append("")
            return
        for row in rows:
            lines.append(f"- **{row.get('title') or 'Untitled'}** — {row.get('author') or 'Unknown author'}")
            if row.get("reason"):
                lines.append(f"  - Reason: {row.get('reason')}")
            for citation in row.get("citations", [])[:3]:
                lines.append(f"  - Citation: {citation}")
            if row.get("evidence"):
                lines.append(f"  - Evidence: {row['evidence'][0][:300]}")
        lines.append("")

    add_section(result.get("books_favouring", []))
    lines += ["## Books criticising", ""]
    add_section(result.get("books_criticising", []))
    lines += ["## Mixed / context-dependent", ""]
    add_section(result.get("books_mixed", []))
    lines += ["## Tensions", ""]
    for tension in result.get("tensions", []):
        lines.append(f"- {tension}")
    lines.append("")
    lines += ["## Method", "", str(result.get("method") or ""), ""]
    return "\n".join(lines)
