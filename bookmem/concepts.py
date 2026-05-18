"""Concept extraction and search for BookMem.

Concepts are derived artefacts. They are generated from canonical Markdown,
chunk metadata and citations, then stored under data/concepts/.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Any

import yaml

from .chunking import chunk_markdown_file, slugify
from .frontmatter import discover_book_files, read_markdown_with_frontmatter
from .config import get_settings


CONCEPT_SCHEMA_VERSION = 1
CONCEPT_EXTRACTOR_VERSION = "0.1.0"


CONCEPT_TYPE_KEYWORDS = {
    "model": [
        "model", "matrix", "map", "loop", "cycle", "pyramid", "ladder", "flywheel",
        "circle", "framework", "system", "quadrant", "curve"
    ],
    "framework": [
        "framework", "method", "process", "approach", "principle", "formula",
        "checklist", "methodology", "protocol"
    ],
    "principle": [
        "principle", "law", "rule", "habit", "effect", "bias", "heuristic",
        "strategy", "practice"
    ],
    "method": [
        "method", "technique", "exercise", "routine", "practice", "process",
        "workflow", "system"
    ],
    "warning": [
        "fallacy", "trap", "risk", "failure", "mistake", "bias", "problem",
        "warning"
    ],
}


CONCEPT_PATTERNS = [
    re.compile(r"\b(?:the\s+)?([A-Z][A-Za-z0-9'’\-]+(?:\s+[A-Z][A-Za-z0-9'’\-]+){1,7})\s+(model|framework|method|principle|system|matrix|loop|cycle|law|effect|rule)\b"),
    re.compile(r"\b(model|framework|method|principle|system|matrix|loop|cycle|law|effect|rule)\s+(?:of|for)\s+([A-Z][A-Za-z0-9'’\-]+(?:\s+[A-Z][A-Za-z0-9'’\-]+){0,7})\b"),
    re.compile(r"\b([A-Z][A-Za-z0-9'’\-]+(?:\s+[A-Z][A-Za-z0-9'’\-]+){1,7})\b"),
]


STOP_CONCEPTS = {
    "United States", "New York", "Table Of Contents", "All Rights Reserved",
    "Kindle Edition", "Chapter One", "Chapter Two", "Chapter Three",
    "Part One", "Part Two", "Part Three", "This Book", "The Book",
}


@dataclass
class ConceptRecord:
    concept_id: str
    name: str
    type: str
    aliases: list[str]
    description: str
    useful_for: list[str]
    limitations: list[str]
    book_id: str
    title: str
    author: str | None
    primary_class: str | None
    topics: list[str]
    source_chunks: list[dict[str, Any]]
    confidence: float
    extractor: str
    review_status: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def concepts_root() -> Path:
    return Path("data/concepts")


def concept_index_path() -> Path:
    return concepts_root() / "concepts.json"


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if value:
        return [str(value).strip()]
    return []


def _normalise_text(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _book_meta(path: Path) -> dict[str, Any]:
    fm, _body, _had = read_markdown_with_frontmatter(path)
    classification = fm.get("classification") if isinstance(fm.get("classification"), dict) else {}
    return {
        "book_id": str(fm.get("book_id") or slugify(f"{fm.get('author', '')}_{fm.get('title', path.stem)}")),
        "title": str(fm.get("title") or path.stem),
        "author": str(fm.get("author")) if fm.get("author") else None,
        "primary_class": str(classification.get("primary_class")) if classification.get("primary_class") else None,
        "topics": _list(classification.get("topics") or fm.get("tags")),
    }


def _concept_type(name: str, context: str) -> str:
    haystack = _normalise_text(f"{name} {context}")
    for type_name, keywords in CONCEPT_TYPE_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return type_name
    return "concept"


def _clean_candidate(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" .,:;—–-()[]{}")
    value = re.sub(r"^(The|A|An)\s+", "", value).strip()
    return value


def _is_good_candidate(value: str) -> bool:
    if not value or value in STOP_CONCEPTS:
        return False
    words = value.split()
    if len(words) < 2 or len(words) > 8:
        return False
    if len(value) < 6:
        return False
    if value.lower().startswith(("chapter ", "part ", "figure ", "table ")):
        return False
    # Avoid sentence fragments that are just capitalised at sentence start.
    common_sentence_starts = {"This", "That", "When", "Where", "What", "How", "Why", "There", "These", "Those"}
    if words[0] in common_sentence_starts and len(words) > 3:
        return False
    return True


def _candidate_concepts(text: str, limit: int = 20) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()

    for pattern in CONCEPT_PATTERNS:
        for match in pattern.finditer(text):
            if len(match.groups()) >= 2 and match.group(2):
                if match.group(1).lower() in {"model", "framework", "method", "principle", "system", "matrix", "loop", "cycle", "law", "effect", "rule"}:
                    candidate = f"{match.group(2)} {match.group(1)}"
                else:
                    candidate = f"{match.group(1)} {match.group(2)}"
            else:
                candidate = match.group(1)

            candidate = _clean_candidate(candidate)
            key = _normalise_text(candidate)
            if key and key not in seen and _is_good_candidate(candidate):
                seen.add(key)
                candidates.append(candidate)
            if len(candidates) >= limit:
                return candidates

    return candidates


def _description_for(name: str, text: str, max_chars: int = 450) -> str:
    # Prefer a sentence containing the candidate.
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
    name_norm = _normalise_text(name)
    for sentence in sentences:
        if name_norm in _normalise_text(sentence) and len(sentence) > 40:
            return sentence[:max_chars].rstrip()
    return (sentences[0] if sentences else text[:max_chars]).strip()[:max_chars].rstrip()


def _useful_for(meta: dict[str, Any], concept_type: str) -> list[str]:
    useful = list(meta.get("topics") or [])
    if concept_type in {"model", "framework", "method"}:
        useful.append("practical application")
        useful.append("planning")
    if concept_type in {"warning", "principle"}:
        useful.append("decision-making")
    return list(dict.fromkeys(useful))[:8]


def extract_concepts_from_book(path: Path, limit: int = 30, write: bool = True, overwrite: bool = True) -> dict[str, Any]:
    meta = _book_meta(path)
    chunks = chunk_markdown_file(path)
    concepts: dict[str, ConceptRecord] = {}

    for chunk in chunks:
        candidates = _candidate_concepts(chunk.text, limit=10)
        for candidate in candidates:
            concept_id = slugify(f"{meta['book_id']}_{candidate}")
            ctype = _concept_type(candidate, chunk.text)
            source_chunk = {
                "chunk_id": chunk.chunk_id,
                "citation": chunk.citation,
                "source_path": str(chunk.source_path),
                "heading_path": chunk.heading_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
            }

            if concept_id in concepts:
                existing = concepts[concept_id]
                if len(existing.source_chunks) < 5:
                    existing.source_chunks.append(source_chunk)
                existing.confidence = min(1.0, existing.confidence + 0.05)
                continue

            aliases = []
            if candidate.lower().startswith("circle of "):
                aliases.append(candidate.replace("Circle of ", "").strip() + " circle")
            if candidate.lower().endswith(" model"):
                aliases.append(candidate[:-6].strip())

            concepts[concept_id] = ConceptRecord(
                concept_id=concept_id,
                name=candidate,
                type=ctype,
                aliases=[alias for alias in aliases if alias and alias != candidate],
                description=_description_for(candidate, chunk.text),
                useful_for=_useful_for(meta, ctype),
                limitations=[],
                book_id=meta["book_id"],
                title=meta["title"],
                author=meta["author"],
                primary_class=meta["primary_class"],
                topics=meta["topics"],
                source_chunks=[source_chunk],
                confidence=0.55 if ctype == "concept" else 0.7,
                extractor="deterministic",
                review_status="machine_draft",
            )

    records = sorted(concepts.values(), key=lambda c: (-c.confidence, c.name.lower()))[:limit]
    payload = {
        "schema_version": CONCEPT_SCHEMA_VERSION,
        "concept_extractor_version": CONCEPT_EXTRACTOR_VERSION,
        "generated_at": utc_now_iso(),
        "book_id": meta["book_id"],
        "title": meta["title"],
        "author": meta["author"],
        "source_path": str(path),
        "concepts": [asdict(record) for record in records],
    }

    if write:
        out_dir = concepts_root() / meta["book_id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "concepts.yaml"
        if overwrite or not out_path.exists():
            out_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
        rebuild_concept_index()

    return payload


def extract_concepts_from_books(root: Path, limit_per_book: int = 30, write: bool = True, overwrite: bool = True) -> list[dict[str, Any]]:
    results = []
    for path in discover_book_files(root):
        results.append(extract_concepts_from_book(path, limit=limit_per_book, write=write, overwrite=overwrite))
    if write:
        rebuild_concept_index()
    return results


def load_concept_files() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    base = concepts_root()
    if not base.exists():
        return records
    for path in sorted(base.glob("*/concepts.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        for concept in data.get("concepts", []) or []:
            if isinstance(concept, dict):
                records.append(concept)
    return records


def rebuild_concept_index(output_path: Path | None = None) -> dict[str, Any]:
    output_path = output_path or concept_index_path()
    records = load_concept_files()
    payload = {
        "schema_version": CONCEPT_SCHEMA_VERSION,
        "concept_extractor_version": CONCEPT_EXTRACTOR_VERSION,
        "generated_at": utc_now_iso(),
        "concept_count": len(records),
        "concepts": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def load_concept_index(path: Path | None = None) -> dict[str, Any]:
    path = path or concept_index_path()
    if not path.exists():
        return rebuild_concept_index(output_path=path)
    return json.loads(path.read_text(encoding="utf-8"))


def search_concepts(query: str, class_code: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    index = load_concept_index()
    query_norm = _normalise_text(query)
    query_terms = set(query_norm.split())
    results = []

    for concept in index.get("concepts", []) or []:
        if class_code and str(concept.get("primary_class")) != str(class_code):
            continue
        fields = [
            concept.get("name", ""),
            " ".join(concept.get("aliases") or []),
            concept.get("description", ""),
            " ".join(concept.get("useful_for") or []),
            " ".join(concept.get("topics") or []),
            concept.get("title", ""),
            concept.get("author", ""),
        ]
        haystack = _normalise_text(" ".join(str(field) for field in fields))
        hay_terms = set(haystack.split())
        score = 0.0
        if query_norm and query_norm in haystack:
            score += 0.7
        if query_terms:
            score += min(0.5, 0.1 * len(query_terms & hay_terms))
        if score:
            item = dict(concept)
            item["score"] = round(min(score, 1.0), 3)
            results.append(item)

    return sorted(results, key=lambda item: (-item["score"], item.get("name", "")))[:limit]


def list_concepts(class_code: str | None = None, concept_type: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    index = load_concept_index()
    concepts = []
    for concept in index.get("concepts", []) or []:
        if class_code and str(concept.get("primary_class")) != str(class_code):
            continue
        if concept_type and str(concept.get("type")) != concept_type:
            continue
        concepts.append(concept)
    return sorted(concepts, key=lambda item: (item.get("primary_class") or "", item.get("title") or "", item.get("name") or ""))[:limit]
