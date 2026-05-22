"""Claims extraction and comparison for BookMem.

Concepts are reusable models/frameworks. Claims are assertions that can be
supported, challenged or compared across books.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

import yaml

from .frontmatter import read_markdown_with_frontmatter
from .chunking import slugify
from .search import search_books
from .audit import append_audit_record


CLAIMS_VERSION = "0.1.0"
CLAIMS_DIR = Path("data/claims")
CLAIMS_INDEX_PATH = CLAIMS_DIR / "claims.yaml"

STANCES = {"supports", "challenges", "qualifies", "neutral"}
CONFIDENCES = {"low", "medium", "high"}


@dataclass
class Claim:
    claim_id: str
    claim: str
    stance: str
    confidence: str
    source_chunks: list[str]
    citation: str | None
    tags: list[str]
    review_status: str
    title: str | None = None
    author: str | None = None
    book_id: str | None = None
    source_path: str | None = None
    heading_path: str | None = None
    evidence: str | None = None
    extracted_at: str | None = None
    extractor: str = "deterministic"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_claims_index() -> None:
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    if not CLAIMS_INDEX_PATH.exists():
        CLAIMS_INDEX_PATH.write_text("schema_version: 1\nclaims: []\n", encoding="utf-8")


def load_claims_index() -> dict[str, Any]:
    ensure_claims_index()
    data = yaml.safe_load(CLAIMS_INDEX_PATH.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("schema_version", 1)
    data.setdefault("claims", [])
    return data


def save_claims_index(data: dict[str, Any]) -> None:
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    data["claims_version"] = CLAIMS_VERSION
    data["updated_at"] = utc_now_iso()
    CLAIMS_INDEX_PATH.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=110),
        encoding="utf-8",
    )


def plain_text(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]+`", " ", text)
    text = re.sub(r"\[[^\]]+\]\([^\)]*\)", "", text)
    text = re.sub(r"[*_>#]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    text = plain_text(text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if len(part.split()) >= 8]


def infer_stance(sentence: str) -> tuple[str, str]:
    s = sentence.lower()
    challenge_terms = ["not", "never", "less useful", "worse", "problem", "fails", "failure", "risk", "danger", "counterproductive", "instead of", "rather than", "myth"]
    qualify_terms = ["depends", "unless", "however", "although", "but", "context", "sometimes", "may", "can", "tradeoff", "trade-off"]
    support_terms = ["should", "must", "is", "are", "improves", "helps", "leads to", "causes", "supports", "requires", "works", "useful", "important", "essential"]

    if any(term in s for term in challenge_terms):
        if any(term in s for term in qualify_terms):
            return "qualifies", "medium"
        return "challenges", "medium"
    if any(term in s for term in qualify_terms):
        return "qualifies", "medium"
    if any(term in s for term in support_terms):
        return "supports", "medium"
    return "neutral", "low"


def sentence_looks_like_claim(sentence: str) -> bool:
    s = sentence.lower()
    words = sentence.split()
    if len(words) < 10 or len(words) > 45:
        return False
    claim_markers = [
        "should", "must", "because", "therefore", "leads to", "causes", "means that",
        "is more", "is less", "are more", "are less", "depends", "requires",
        "helps", "improves", "fails", "risk", "important", "essential", "useful",
        "rather than", "instead of", "not enough", "better", "worse",
    ]
    return any(marker in s for marker in claim_markers)


def infer_tags(sentence: str, fallback: list[str]) -> list[str]:
    s = sentence.lower()
    tags = []
    candidates = {
        "goals": ["goal", "goals"],
        "systems": ["system", "systems"],
        "habits": ["habit", "habits"],
        "risk": ["risk", "risks"],
        "finance": ["money", "invest", "investment", "finance", "market"],
        "energy": ["energy", "motivation", "focus"],
        "leadership": ["leader", "leadership", "team", "management"],
        "learning": ["learn", "learning", "skill", "practice"],
    }
    for tag, terms in candidates.items():
        if any(term in s for term in terms):
            tags.append(tag)
    for tag in fallback:
        if tag not in tags:
            tags.append(tag)
    return tags[:8]


def extract_claims(book_path: Path, limit: int = 40, write: bool = True, tag: list[str] | None = None) -> dict[str, Any]:
    frontmatter, body, _had = read_markdown_with_frontmatter(book_path)
    title = str(frontmatter.get("title") or book_path.stem)
    author = str(frontmatter.get("author") or "") or None
    book_id = str(frontmatter.get("book_id") or slugify(f"{author or ''}_{title}"))
    classification = frontmatter.get("classification") if isinstance(frontmatter.get("classification"), dict) else {}
    fallback_tags = tag or [str(t) for t in (classification.get("topics") or [])[:5]]

    claims = []
    seen = set()
    for idx, sentence in enumerate(split_sentences(body)):
        if not sentence_looks_like_claim(sentence):
            continue
        claim_text = sentence.strip()
        key = claim_text.lower()
        if key in seen:
            continue
        seen.add(key)

        stance, confidence = infer_stance(claim_text)
        claim_id = slugify(f"{book_id}_{idx}_{claim_text[:48]}")
        citation = f"{title}" + (f" — {author}" if author else "")
        claims.append(
            asdict(
                Claim(
                    claim_id=claim_id,
                    claim=claim_text,
                    stance=stance,
                    confidence=confidence,
                    source_chunks=[],
                    citation=citation,
                    tags=infer_tags(claim_text, fallback_tags),
                    review_status="machine_draft",
                    title=title,
                    author=author,
                    book_id=book_id,
                    source_path=str(book_path),
                    heading_path=None,
                    evidence=claim_text,
                    extracted_at=utc_now_iso(),
                )
            )
        )
        if len(claims) >= limit:
            break

    added = claims
    if write:
        data = load_claims_index()
        existing = [item for item in data.get("claims", []) if isinstance(item, dict)]
        existing_ids = {item.get("claim_id") for item in existing}
        added = []
        for claim in claims:
            if claim["claim_id"] not in existing_ids:
                existing.append(claim)
                added.append(claim)
        data["claims"] = existing
        save_claims_index(data)
        append_audit_record(
            action="claims.extract",
            status="ok",
            changed_files=[CLAIMS_INDEX_PATH],
            target=str(book_path),
            message=f"Extracted {len(added)} claim(s)",
            details={"book": str(book_path), "candidates": len(claims), "added": len(added)},
        )

    return {"book": str(book_path), "count": len(claims), "added": len(added), "claims": claims, "wrote": write}


def all_claims() -> list[dict[str, Any]]:
    return [item for item in load_claims_index().get("claims", []) if isinstance(item, dict)]


def search_claims(query: str, limit: int = 20, stance: str | None = None) -> list[dict[str, Any]]:
    q_terms = [term for term in re.findall(r"\w+", query.lower()) if len(term) > 2]
    rows = []
    for claim in all_claims():
        if stance and claim.get("stance") != stance:
            continue
        haystack = " ".join(
            str(claim.get(key) or "")
            for key in ("claim", "citation", "title", "author", "heading_path", "evidence")
        ).lower()
        haystack += " " + " ".join(str(t).lower() for t in claim.get("tags", []) or [])
        score = sum(1 for term in q_terms if term in haystack)
        if query.lower() in haystack:
            score += 3
        if score:
            rows.append({**claim, "score": score})
    rows.sort(key=lambda item: (-item["score"], item.get("title") or ""))
    if rows:
        return rows[:limit]

    # Fallback: use corpus search to create ephemeral claim-like candidates.
    fallback = []
    for row in search_books(query, limit=limit):
        text = plain_text(row.get("text") or row.get("excerpt") or "")
        sentences = [s for s in split_sentences(text) if sentence_looks_like_claim(s)]
        sentence = sentences[0] if sentences else text[:400]
        inferred_stance, confidence = infer_stance(sentence)
        fallback.append({
            "claim_id": row.get("chunk_id"),
            "claim": sentence,
            "stance": inferred_stance,
            "confidence": confidence,
            "source_chunks": [row.get("chunk_id")] if row.get("chunk_id") else [],
            "citation": row.get("citation"),
            "tags": infer_tags(sentence, []),
            "review_status": "machine_draft",
            "title": row.get("title"),
            "author": row.get("author"),
            "book_id": row.get("book_id"),
            "source_path": row.get("source_path"),
            "heading_path": row.get("heading_path"),
            "evidence": text[:600],
            "score": 0,
        })
    return fallback


def compare_claims(topic: str, limit: int = 20) -> dict[str, Any]:
    rows = search_claims(topic, limit=limit * 3)
    grouped = {
        "supports": [],
        "challenges": [],
        "qualifies": [],
        "neutral": [],
    }
    for row in rows:
        grouped.setdefault(row.get("stance") or "neutral", []).append(row)

    tensions = infer_claim_tensions(topic, grouped)

    result = {
        "schema_version": 1,
        "claims_version": CLAIMS_VERSION,
        "topic": topic,
        "supports": grouped.get("supports", [])[:limit],
        "challenges": grouped.get("challenges", [])[:limit],
        "qualifies": grouped.get("qualifies", [])[:limit],
        "neutral": grouped.get("neutral", [])[:limit],
        "tensions": tensions,
        "review_status": "machine_draft",
        "method": "deterministic claim stance search over extracted claims with corpus fallback",
    }
    append_audit_record(
        action="claims.compare",
        status="ok",
        changed_files=[],
        target=topic,
        message=f"Compared claims for {topic}",
        details={key: len(result[key]) for key in ("supports", "challenges", "qualifies", "neutral")},
    )
    return result


def infer_claim_tensions(topic: str, grouped: dict[str, list[dict[str, Any]]]) -> list[str]:
    tensions = []
    if grouped.get("supports") and grouped.get("challenges"):
        tensions.append(f"The corpus contains claims both supporting and challenging '{topic}'.")
    if grouped.get("qualifies"):
        tensions.append(f"Some claims treat '{topic}' as context-dependent rather than simply true or false.")
    topic_norm = topic.lower()
    if "goal" in topic_norm and (grouped.get("supports") or grouped.get("challenges")):
        tensions.append("Goals may provide direction, while systems and habits may determine whether progress is sustained.")
    if "compound" in topic_norm or "interest" in topic_norm:
        tensions.append("Compounding can be powerful, but outcomes depend on time horizon, consistency, risk and fees.")
    if "risk" in topic_norm:
        tensions.append("Risk can be a source of return, but unmanaged risk can undermine the intended outcome.")
    if not tensions:
        tensions.append(f"No strong claim-level disagreement was detected for '{topic}'.")
    seen = set()
    out = []
    for item in tensions:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out[:8]


def render_claims_compare_markdown(result: dict[str, Any]) -> str:
    lines = [
        "---",
        "type: bookmem-claims-comparison",
        f"topic: {result.get('topic')}",
        f"review_status: {result.get('review_status')}",
        "---",
        "",
        f"# Claims Comparison — {result.get('topic')}",
        "",
    ]

    for label, key in (("Supporting claims", "supports"), ("Challenging claims", "challenges"), ("Qualifying claims", "qualifies"), ("Neutral claims", "neutral")):
        lines += [f"## {label}", ""]
        rows = result.get(key, []) or []
        if not rows:
            lines += ["_None found._", ""]
            continue
        for row in rows:
            lines.append(f"- **{row.get('claim')}**")
            lines.append(f"  - Source: {row.get('title') or 'Untitled'} — {row.get('author') or 'Unknown author'}")
            if row.get("citation"):
                lines.append(f"  - Citation: {row.get('citation')}")
            lines.append(f"  - Confidence: {row.get('confidence')}")
        lines.append("")

    lines += ["## Tensions", ""]
    for tension in result.get("tensions", []):
        lines.append(f"- {tension}")
    lines.append("")
    return "\n".join(lines)
